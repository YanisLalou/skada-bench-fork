"""
This script processes cross-validation results from Benchopt output files,
extracting and organizing the CV splits information into a readable CSV format.

The script performs the following steps:
1. Loads data from a specified directory containing Benchopt output files
   (CSV or Parquet format)
2. Extracts and processes the cross-validation results for each split
3. Cleans and organizes the data into a structured format
4. Exports the processed results to a CSV file

Usage:
    python retrieve_benchopt_results_splits.py \
        --directory <input_directory> \
        --output <output_directory> \
        --file_name <output_filename>

Arguments:
    --directory: Path to the directory containing Benchopt output files.
                Default is '../outputs'.
    --output:    Path to the directory where the processed CSV file will be
                saved. Default is './cleaned_outputs'.
    --file_name: Name of the output file. Default is 'results'.

Example:
    python retrieve_benchopt_results_splits.py \
        --directory ../outputs \
        --output ./cleaned_outputs \
        --file_name cv_results
"""

import os
import argparse

from _solvers_scorers_registry import (
    DA_TECHNIQUES,
    ESTIMATOR_DICT,
)

from _utils import (
    process_files_in_directory,
    regex_match,
)


def clean_benchopt_df(df):
    # We remove '[param_grid=...]' from the dataset name
    df['solver_name'] = df['solver_name'].map(
        lambda x: (x.split('[param_grid=')[0]))

    df.rename(columns={'data_name': 'dataset'}, inplace=True)
    df.rename(columns={'solver_name': 'estimator'}, inplace=True)

    df = df.reset_index(drop=True)

    # Add type column
    # Create a reverse lookup dictionary
    reverse_lookup = {
        solver: technique for technique, solvers in DA_TECHNIQUES.items()
        for solver in solvers
    }
    df['type'] = df['estimator'].map(reverse_lookup)

    # Set to 'Unknown' for the rest
    df['type'].fillna('Unknown', inplace=True)

    # Rename solvers with ESTIMATOR_DICT
    df['estimator'] = df['estimator'].map(lambda x: ESTIMATOR_DICT.get(x, x))

    # Function to extract shift value
    def extract_shift(dataset):
        # Extract random state if it exists
        random_state = None
        if 'random_state=' in dataset:
            try:
                random_state = dataset.split('random_state=')[1].split(']')[
                    0].split(',')[0]
            except IndexError:
                pass

        # Extract shift value based on dataset type
        if 'shift' in dataset:
            shift = dataset.split('shift=')[1].strip(']')
        elif 'source_target' in dataset:
            regex = r".*source_target=\('([^']+)', '([^']+)'\).*"
            shift = regex_match(regex, dataset)
        elif 'subject_id' in dataset:
            shift = dataset.split('subject_id=')[1].strip(']')
        else:
            return None

        # Combine shift and random_state if random_state exists
        if random_state is not None:
            return f"{shift}_randomstate={random_state}"
        return shift

    # Add shift as a new column
    df['shift'] = df['dataset'].apply(extract_shift)

    # Remove the params in the dataset name
    df['dataset'] = df['dataset'].apply(lambda x: x.split('[')[0])

    # Reorganize df
    selected_cols = ['dataset', 'shift', 'estimator', 'scorer',
                     'type', 'idx_rep', 'split', 'grid_split', 'results']

    df = df[selected_cols]

    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process Benchopt output files to extract and organize "
                   "cross-validation results"
    )

    parser.add_argument(
        "--directory",
        type=str,
        help="Path to the directory containing Benchopt output files",
        default='../outputs'
    )

    parser.add_argument(
        "--output",
        type=str,
        help="Path to the output directory for processed results",
        default='./cleaned_outputs'
    )

    parser.add_argument(
        "--file_name",
        type=str,
        help="Name of the output CSV file",
        default="results"
    )

    args = parser.parse_args()

    # Step 1: Load the Data
    # Load the data from the specified directory
    df = process_files_in_directory(
        args.directory, processing_type='retrieve_cv'
    )

    # Step 2: Clean the dataframe
    df = clean_benchopt_df(df)

    # Step 3: Export to CSV
    output_directory = args.output

    os.makedirs(output_directory, exist_ok=True)

    df.to_csv(f'{output_directory}/{args.file_name}.csv', index=False)