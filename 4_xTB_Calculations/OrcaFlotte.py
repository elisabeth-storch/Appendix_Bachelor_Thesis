import os
import subprocess
import time
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
import glob
import argparse
import logging
from datetime import datetime
import pathlib
import signal
import sys
import random  # Für die Zufallsauswahl

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('orca_queue.log')
    ]
)
logger = logging.getLogger('orca_queue')

class OrcaJobQueue:
    def __init__(self, orca_path=None, max_workers=None, output_dir=None):
        """
        Initialize the ORCA job queue.
        
        Parameters:
        orca_path (str): Path to the ORCA executable
        max_workers (int): Maximum number of parallel jobs (default: CPU count - 1)
        output_dir (str): Directory for output files (default: same as input files)
        """
        # Determine number of cores
        if max_workers is None:
            max_workers = max(1, multiprocessing.cpu_count() - 1)
        self.max_workers = max_workers
        
        # Set ORCA path
        self.orca_path = orca_path
        
        # Set output directory
        self.output_dir = output_dir
        
        # Initialize job lists
        self.pending_jobs = []
        self.completed_jobs = []
        self.failed_jobs = []

        # Add tracking for active processes
        self.active_processes = {}
        self.shutdown_requested = False
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

    def handle_shutdown(self, sig, frame):
        """Handle shutdown signals gracefully"""
        if self.shutdown_requested:
            logger.warning("Forcing immediate shutdown!")
            sys.exit(1)
            
        logger.warning("\nShutdown requested! Finishing current jobs and cleaning up...")
        self.shutdown_requested = True
        
        # Try to terminate any active ORCA processes
        for job_name, proc in self.active_processes.items():
            logger.info(f"Terminating process for job {job_name}")
            try:
                proc.terminate()
            except:
                pass
        
        logger.info("Shutdown complete. Exiting.")
        sys.exit(0)

    def add_job(self, input_file):
        """Add a job to the queue"""
        self.pending_jobs.append(input_file)
        logger.info(f"Added job to queue: {os.path.basename(input_file)}")
    
    def add_jobs_from_directory(self, base_dir, recursive=True):
        """
        Add all .inp files from a directory and its subdirectories,
        ABER prüfe: wenn <Basename>.xyz schon existiert, füge den Job nicht hinzu.
        """
        base_dir = os.path.abspath(base_dir)
        if not os.path.isdir(base_dir):
            logger.error(f"Directory not found: {base_dir}")
            return 0

        input_files = []

        if recursive:
            for root, _, files in os.walk(base_dir):
                for file in files:
                    if file.endswith('.inp'):
                        input_files.append(os.path.join(root, file))
        else:
            input_files = glob.glob(os.path.join(base_dir, '*.inp'))

        added_count = 0
        for input_file in input_files:
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            xyz_file = os.path.join(os.path.dirname(input_file), f"{base_name}.xyz")

            # Nur hinzufügen, wenn KEINE .xyz-Datei existiert
            if not os.path.isfile(xyz_file):
                self.add_job(input_file)
                added_count += 1
            else:
                logger.info(f"Überspringe Job für {base_name}, da {xyz_file} bereits existiert.")

        logger.info(f"Added {added_count} jobs from directory '{base_dir}' (recursive={recursive})")
        return added_count
    
    def add_jobs_from_glob(self, pattern):
        """Add multiple jobs using a glob pattern"""
        input_files = glob.glob(pattern, recursive=True)
        added_count = 0
        for input_file in input_files:
            base_name = os.path.splitext(os.path.basename(input_file))[0]
            xyz_file = os.path.join(os.path.dirname(input_file), f"{base_name}.xyz")
            if not os.path.isfile(xyz_file):
                self.add_job(input_file)
                added_count += 1
            else:
                logger.info(f"Überspringe Job für {base_name}, da {xyz_file} bereits existiert.")
        logger.info(f"Added {added_count} jobs from pattern '{pattern}'")
        return added_count
    
    def run_job(self, input_file):
        """
        Run a single ORCA calculation job.
        
        Parameters:
        input_file (str): Path to the ORCA input file
        
        Returns:
        dict: Result information including success status and output path
        """
        if self.shutdown_requested:
            return {'job_name': os.path.basename(input_file).replace('.inp', ''), 
                    'success': False, 'error': 'Shutdown requested'}

        job_name = os.path.basename(input_file).replace('.inp', '')
        start_time = time.time()  # Define start time for job execution tracking
        
        # Determine output directory and create if needed
        output_dir = self.output_dir if self.output_dir else os.path.dirname(input_file)
        os.makedirs(output_dir, exist_ok=True)
        
        # Prepare output file path
        output_file = os.path.join(output_dir, f"{job_name}.out")
        
        try:
            # Check if ORCA path exists
            if not self.orca_path or not os.path.exists(self.orca_path):
                raise FileNotFoundError(f"ORCA executable not found at: {self.orca_path}")
            
            # Set up environment for ORCA
            env = os.environ.copy()
            orca_dir = os.path.dirname(self.orca_path)
            env['PATH'] = f"{orca_dir};{env.get('PATH', '')}"
            
            # Change to the directory of the input file
            working_dir = os.path.dirname(input_file)
            
            # Run ORCA with the input file and redirect output
            process = subprocess.Popen(
                [self.orca_path, os.path.basename(input_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                cwd=working_dir,  # Run from the input file's directory
                env=env
            )
            
            # Store the process in active_processes
            self.active_processes[job_name] = process
            
            stdout, stderr = process.communicate()
            
            # Remove from active processes
            self.active_processes.pop(job_name, None)
            
            # Write output to file
            with open(output_file, 'w') as f:
                f.write(stdout)
            
            # Write errors if any
            if stderr:
                with open(f"{output_file}.err", 'w') as f:
                    f.write(stderr)
            
            elapsed_time = time.time() - start_time
            
            # Check for "HURRAY" in the output file to determine success
            hurray_found = "HURRAY" in stdout
            process_success = process.returncode == 0
            
            # Success only if both return code is 0 and HURRAY is found
            success = process_success and hurray_found
            
            result = {
                'job_name': job_name,
                'success': success,
                'process_success': process_success,  # Did the process complete without errors
                'hurray_found': hurray_found,       # Was "HURRAY" found in output
                'input_file': input_file,
                'output_file': output_file,
                'time_taken': elapsed_time,
                'return_code': process.returncode,
                'completion_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            if success:
                status = "completed successfully (HURRAY found)"
            elif process_success:
                status = "completed but without HURRAY"
            else:
                status = "failed with return code " + str(process.returncode)
            logger.info(f"Job {job_name} {status} in {elapsed_time:.2f} seconds")
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error in job {job_name}: {error_msg}")
            
            # Make sure to remove from active processes
            self.active_processes.pop(job_name, None)
            return {
                'job_name': job_name,
                'success': False,
                'process_success': False,
                'hurray_found': False,
                'input_file': input_file,
                'error': error_msg,
                'completion_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    
    def process_result(self, result):
        """Process a completed job result"""
        if result['success']:
            self.completed_jobs.append(result)
            # Clean up files for successful jobs
            self.cleanup_job_files(result)
        else:
            self.failed_jobs.append(result)

    def cleanup_job_files(self, job_info):
        """Clean up unnecessary files after job completion"""
        try:
            # Get the directory and base name of the job
            job_dir = os.path.dirname(job_info['input_file'])
            base_name = os.path.basename(job_info['input_file']).replace('.inp', '')
            
            # Get all files in the directory that start with the base name
            all_files = [f for f in os.listdir(job_dir) if f.startswith(base_name)]
            
            # Keep track of deleted files for logging
            deleted_files = []
            
            # Check each file
            for file in all_files:
                # If the file doesn't end with .out, .inp, or .xyz, delete it
                if not (file.endswith('.out') or file.endswith('.inp') or file.endswith('.xyz')):
                    file_path = os.path.join(job_dir, file)
                    os.remove(file_path)
                    deleted_files.append(file)
            
            if deleted_files:
                logger.info(f"Cleaned up {len(deleted_files)} files for job {base_name}: {', '.join(deleted_files)}")
        
        except Exception as e:
            logger.error(f"Error cleaning up files for {job_info['job_name']}: {str(e)}")
    
    def run_all_jobs(self):
        """Run all pending jobs using process pool executor"""
        logger.info(f"Starting job processing with {self.max_workers} workers")
        logger.info(f"Pending jobs: {len(self.pending_jobs)}")
        logger.info(f"Press Ctrl+C to gracefully stop processing")
        
        # Create a copy of pending jobs to process
        jobs_to_process = self.pending_jobs.copy()
        
        
        # Clear pending jobs list as we'll process them
        self.pending_jobs = []
        
        total_jobs = len(jobs_to_process)
        processed_jobs = 0
        summary_interval = 200  # Print summary every 200 jobs
        
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all jobs and get the futures
            futures = [executor.submit(self.run_job, job) for job in jobs_to_process]
            
            # Process results as they complete
            for future in futures:
                try:
                    result = future.result()
                    self.process_result(result)
                    
                    # Count processed jobs
                    processed_jobs += 1
                    
                    # Print progress
                    if processed_jobs % 10 == 0:
                        logger.info(f"Progress: {processed_jobs}/{total_jobs} jobs processed ({processed_jobs/total_jobs*100:.1f}%)")
                    
                    # Print intermediate summary every summary_interval jobs
                    if processed_jobs % summary_interval == 0:
                        logger.info(f"\n--- INTERMEDIATE SUMMARY (after {processed_jobs}/{total_jobs} jobs) ---")
                        self.print_summary(is_final=False)
                        
                except Exception as exc:
                    logger.error(f"Job processing exception: {exc}")
                    processed_jobs += 1
        
        # Print final summary after completion
        logger.info("\n--- FINAL JOB SUMMARY ---")
        self.print_summary(is_final=True)
    
    def print_summary(self, is_final=True):
        """
        Print a summary of job completions
        
        Parameters:
        is_final (bool): Whether this is the final summary or an intermediate one
        """
        # Count jobs with different completion statuses
        completed_count = len(self.completed_jobs)
        failed_count = len(self.failed_jobs)
        
        # Count jobs that completed but didn't have HURRAY
        completed_without_hurray = [j for j in self.failed_jobs if j.get('process_success', False) and not j.get('hurray_found', False)]
        without_hurray_count = len(completed_without_hurray)
        
        # Count jobs that had process errors
        process_error_count = failed_count - without_hurray_count
        
        logger.info(f"Total jobs processed: {completed_count + failed_count}")
        logger.info(f"Successful jobs (HURRAY found): {completed_count}")
        logger.info(f"Jobs completed but without HURRAY: {without_hurray_count}")
        logger.info(f"Jobs failed with process errors: {process_error_count}")
        logger.info(f"Pending jobs: {len(self.pending_jobs)}")
        
        # For intermediate summaries, don't show detailed error lists
        if not is_final:
            return
            
        if completed_without_hurray:
            logger.warning("\nJobs completed without HURRAY:")
            for job in completed_without_hurray:
                logger.warning(f"  - {job['job_name']}")
        
        # List jobs that had process errors
        process_errors = [j for j in self.failed_jobs if not j.get('process_success', False)]
        if process_errors:
            logger.warning("\nJobs with process errors:")
            for job in process_errors:
                error_msg = job.get('error', 'Unknown error')
                logger.warning(f"  - {job['job_name']}: {error_msg}")

def main():
    parser = argparse.ArgumentParser(description="ORCA Job Queue Manager")
    parser.add_argument("--orca-path", "-o", type=str, default="C:\\orca6\\orca.exe",
                        help="Path to the ORCA executable (default: C:\\orca6\\orca.exe)")
    parser.add_argument("--input-dir", "-i", type=str, default="<path_to_folder_Complexes>",
                        help="Directory containing input files (will search recursively)")
    parser.add_argument("--pattern", "-p", type=str, default=None, 
                        help="Glob pattern to find input files (default: '*.inp')")
    parser.add_argument("--output-dir", "-d", type=str, default="<path_to_folder_xTB_Calculations_done>",
                        help="Directory for output files (default: same as input files)")
    parser.add_argument("--max-workers", "-w", type=int, 
                        help=f"Maximum number of parallel jobs (default: CPU count - 1)")
    parser.add_argument("--no-recursive", action="store_true",
                        help="Do not search recursively in subdirectories")
    
    args = parser.parse_args()
    
    # Create job queue
    job_queue = OrcaJobQueue(
        orca_path=args.orca_path,
        max_workers=args.max_workers,
        output_dir=args.output_dir
    )
    
    # Add jobs based on input method
    num_jobs = 0
    if args.input_dir:
        # Add jobs from directory
        num_jobs = job_queue.add_jobs_from_directory(
            args.input_dir, 
            recursive=not args.no_recursive
        )
    elif args.pattern:
        # Add jobs from glob pattern
        num_jobs = job_queue.add_jobs_from_glob(args.pattern)
    else:
        # Default: use current directory
        num_jobs = job_queue.add_jobs_from_directory('.', recursive=not args.no_recursive)
    
    if num_jobs == 0:
        logger.warning("No input files found!")
        return
    
    # Run all jobs
    job_queue.run_all_jobs()

if __name__ == "__main__":
    main()