# Quick Start Guide: Adding New Marker Files

For detailed instructions, refer to the detailed [README file](src/markers/input/README.md).

## Steps to Add New Marker Files

1. **Create a New Branch**  
   - Create a new branch in your repository for your changes.

2. **Prepare Input Data**  
   - Add your marker data file(s) to the `src/markers/input` directory.  
   - Ensure the file includes the required columns: `clusterName`, `f_score`, `NSForest_markers`, and `cxg_dataset_title`.

3. **Add Metadata**  
   - Update the `src/markers/input/metadata.csv` file with a new row describing your input file.  
   - Include fields like `file_name`, `Organ`, `Species`, and others as specified in the detailed guide.

4. **Commit and Push Changes**  
   - Commit your changes and push them to your branch.

5. **Create a Pull Request**  
   - Open a pull request to merge your branch into the main repository.  
   - This will trigger GitHub Actions to validate your input files and metadata.

6. **Address Validation Issues**  
   - Review the validation results from GitHub Actions and fix any reported issues.

7. **Submit for Review**  
   - Once validation passes, request a review for your pull request.