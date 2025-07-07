import os
import glob
import shutil
import re
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('goat_conversion.log')
    ]
)
logger = logging.getLogger('goat_converter')

def extract_geometry_type(file_path):
    """
    Extract geometry type from file path and return its polyhedral abbreviation.
    Example: /path/to/XTB/Linear/Ag/Ag_1_Cl_Cl/file.xyz -> LN
    """
    # Define mapping of geometry types to their polyhedral abbreviations
    geometry_abbreviations = {
        "Linear": "L",
        "Oktaedrisch": "OC",
        "Quadratisch_Planar": "SP", 
        "Quadratisch_Pyramidal": "SPY",
        "T_Foermig": "TS",
        "Tetraedrisch": "T",
        "Trigonal_Bipyramidal": "TBPY",
        "Trigonal_Planar": "TP",
        "Trigonal_Prismatisch": "TPR",
        "Trigonal_Pyramidal": "TPY"
    }
    
    parts = Path(file_path).parts
    
    # Look for known geometry patterns in path
    for part in parts:
        if part in geometry_abbreviations:
            return geometry_abbreviations[part]
    
    return "UNK"  # Unknown geometry

def read_xyz_file(xyz_path):
    """Read an XYZ file and return atom count, title and coordinates"""
    with open(xyz_path, 'r') as f:
        lines = f.readlines()
    
    if len(lines) < 2:
        raise ValueError(f"Invalid XYZ file: {xyz_path}")
    
    atom_count = int(lines[0].strip())
    title = lines[1].strip()
    coordinates = [line.strip() for line in lines[2:] if line.strip()]
    
    return atom_count, title, coordinates

def create_goat_input(xyz_path, original_inp_path=None, charge=None, multiplicity=None):
    """Create GOAT input content from XYZ file"""
    atom_count, title, coordinates = read_xyz_file(xyz_path)
    
    # Try to determine charge and multiplicity from original input file if available
    if original_inp_path and os.path.exists(original_inp_path):
        try:
            with open(original_inp_path, 'r') as f:
                content = f.read()
                # Look for charge and multiplicity in "* xyz <charge> <multiplicity>" format
                xyz_match = re.search(r'\*\s*xyz\s+(-?\d+)\s+(\d+)', content)
                if xyz_match:
                    charge = int(xyz_match.group(1))
                    multiplicity = int(xyz_match.group(2))
        except:
            logger.warning(f"Could not parse original input file: {original_inp_path}")
    
    # If charge or multiplicity not found, return None instead of using default values
    if charge is None or multiplicity is None:
        return None
    
    # Create GOAT input content
    input_content = [
        "!GOAT XTB TightSCF",
        "%PAL NPROCS 8 END",
        "%maxcore 3000",
        "%GOAT",
        "NWORKERS 8",
        "AUTOWALL TRUE",
        "END",
        f"* xyz {charge} {multiplicity}",
    ]
    
    # Add coordinates
    input_content.extend(coordinates)
    input_content.append("*")
    
    return '\n'.join(input_content)

def check_successful_calculation(out_path):
    """Check if ORCA calculation was successful by looking for key strings"""
    try:
        with open(out_path, 'r') as f:
            content = f.read()
            has_hurray = "HURRAY" in content
            has_terminated = "ORCA TERMINATED NORMALLY" in content
            return has_hurray and has_terminated
    except:
        return False

def find_xyz_for_output(out_path):
    """Find corresponding XYZ file for a given output file"""
    base_path = os.path.splitext(out_path)[0]
    xyz_path = base_path + ".xyz"
    if os.path.exists(xyz_path):
        return xyz_path
    return None

def process_directory(base_dir, goat_dir="<GOAT_Input>", test_mode=False, limit=5):  # Path to output containing the GOAT input files
    """Process all XTB calculations in the 'Linear' subdirectory."""
    # Restrict processing to the 'Linear' subdirectory
    linear_dir = os.path.join(base_dir, "<Linear>")  # Path to the 'Linear' subdirectory 
    if not os.path.exists(linear_dir):
        logger.error(f"The 'Linear' subdirectory does not exist in {base_dir}.")
        return 0, 0

    # Create GOAT output directory if it doesn't exist
    goat_output_dir = goat_dir
    os.makedirs(goat_output_dir, exist_ok=True)

    # Find all .out files in the 'Linear' subdirectory
    out_files = []
    for root, _, files in os.walk(linear_dir):
        for file in files:
            if file.endswith('.out'):
                out_files.append(os.path.join(root, file))

    logger.info(f"Found {len(out_files)} output files to check in 'Linear'.")
    logger.info(f"GOAT input files will be saved to: {goat_output_dir}")

    if test_mode:
        logger.info(f"*** TEST MODE: Will only process up to {limit} successful files ***")

    successful = 0
    failed = 0

    # Process each output file
    for out_path in out_files:
        try:
            # Check if we've reached the limit in test mode
            if test_mode and successful >= limit:
                logger.info(f"Test mode: Reached limit of {limit} files. Stopping.")
                break

            # Check if the calculation was successful
            was_successful = check_successful_calculation(out_path)
            if not was_successful:
                logger.debug(f"Skipping non-successful calculation: {out_path}")
                failed += 1
                continue

            # Find the corresponding XYZ file
            xyz_path = find_xyz_for_output(out_path)
            if not xyz_path:
                logger.warning(f"No XYZ file found for successful calculation: {out_path}")
                failed += 1
                continue

            # Get original input file path
            input_path = os.path.splitext(out_path)[0] + ".inp"

            # Extract geometry type and base filename
            geom_type = extract_geometry_type(xyz_path)
            base_name = os.path.basename(os.path.splitext(xyz_path)[0])

            # Create new filename with geometry prefix
            new_filename = f"{geom_type}_{base_name}.inp"
            new_path = os.path.join(goat_output_dir, new_filename)

            # Create GOAT input content
            goat_content = create_goat_input(xyz_path, input_path)
            if goat_content is None:
                logger.warning(f"Skipping file due to missing charge or multiplicity: {xyz_path}")
                failed += 1
                continue

            # Write to new file
            with open(new_path, 'w') as f:
                f.write(goat_content)

            logger.info(f"Created GOAT input file: {new_path}")
            successful += 1

        except Exception as e:
            logger.error(f"Error processing {out_path}: {str(e)}")
            failed += 1

    # Log summary with test mode indication
    if test_mode:
        logger.info(f"TEST MODE: Conversion complete: {successful} files converted successfully (limited to {limit}), {failed} failed")
    else:
        logger.info(f"Conversion complete: {successful} files converted successfully, {failed} failed")

    return successful, failed

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Convert successful XTB calculations to GOAT inputs")
    parser.add_argument("--dir", "-d", default="<XTB>") # Path to the base directory containing the XTB calculations
    parser.add_argument("--goat-dir", "-g", default="<GOAT_Inputs>", 
                        help="Output directory for GOAT input files (default: GOAT_Inputs)")
    parser.add_argument("--test-mode", "-t", action="store_true", help="Enable test mode (process limited number of files)")
    parser.add_argument("--limit", "-l", type=int, default=5, help="Limit number of files to process in test mode (default: 5)")

    args = parser.parse_args()

    # Absolute path to the base directory
    base_dir = os.path.abspath(args.dir)
    if not os.path.isdir(base_dir):
        logger.error(f"Directory not found: {base_dir}")
        return

    logger.info(f"Processing directory: {base_dir}")
    successful, failed = process_directory(base_dir, args.goat_dir, args.test_mode, args.limit)

    if successful > 0:
        logger.info(f"Successfully converted {successful} files. GOAT input files are in the directory: {args.goat_dir}")
    else:
        logger.warning("No successful calculations were found or converted.")

if __name__ == "__main__":
    main()