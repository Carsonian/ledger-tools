import pandas as pd

import os
import subprocess
import tempfile


def clean_csv(csv_path):

    # Read the csv into a df
    df = pd.read_csv(csv_path)

    # Format dates as datetime
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['datetime'] = df['datetime'].dt.strftime('%m/%d/%Y')

    # Edit the category column to: "Expenses:{category}"
    df['category'] = 'Expenses:' + df['category'].astype(str)

    # Add the currency to the money column
    df['money'] = df['money'].astype(str) + ' ' + df['currency'].astype(str)

    # Rename the columns
    df.rename(columns={'wallet': 'Country',
                       'category': 'Account',
                       'datetime': 'date',
                       'money': 'debit',
                       'place': 'City'}, inplace=True)

    # Delete the columns we don't need
    df.drop('currency', axis=1, inplace=True)

    # Create a tempfile to save the csv to
    tmp_clean_csv = tempfile.NamedTemporaryFile(delete=False)

    df.to_csv(tmp_clean_csv, index=False)

    return tmp_clean_csv


def run_ledger_convert(tmp_clean_csv, csv_path):
    convert_cmd = r'ledger convert -f' + r' /home/carson/Files/accounting/asia-trip.ledger ' + tmp_clean_csv.name + r' --input-date-format "%m/%d/%Y"'

    ledger_file = subprocess.check_output(convert_cmd, shell=True).decode('utf-8')

    final_ledger_file = clean_ledger_file(ledger_file)

    # Change the filename from .csv to .ledger
    output_dir = os.path.splitext(csv_path)[0]+'.ledger'

    # Write the conversion output to the output_dir
    with open(output_dir, "w") as text_file:
        text_file.write(final_ledger_file)

    # Close and delete the tempfile
    tmp_clean_csv.close()
    os.unlink(tmp_clean_csv.name)


def clean_ledger_file(ledger_file):

    split_file = ledger_file.splitlines()

    # Remove all asterix
    split_file = [s.replace('*', '') for s in split_file]

    # Replace equity unknown with assets cash
    split_file = [s.replace('Equity:Unknown', 'Assets:Cash') for s in split_file]

    # Replace Expenses:City Transit and Expenses:Train with Expenses:Transportation:x
    split_file = [s.replace('Expenses:City Transit', 'Expenses:Transportation:City Transit') for s in split_file]
    split_file = [s.replace('Expenses:Train', 'Expenses:Transportation:Train') for s in split_file]

    # Replace Expenses:Unknown with the proper account
    for id_item, item in enumerate(split_file):
        if 'Expenses:Unknown' in item:
            # Get the string 3 items back if it contains Account:
            x = 0
            while 'Account:' not in split_file[id_item - x]:
                x += 1

            account = split_file[id_item - x]
            account = account.replace('; Account: ', '')
            account = account.strip()

            split_file[id_item] = item.replace("Expenses:Unknown", account)

            # Pop the account line now that we don't need it
            split_file.pop(id_item - x)

    # Rejoin all the lines back together
    clean_file = '\n'.join(split_file)

    return clean_file


def main():

    csv_path = "/home/carson/Downloads/MoneyWallet_export_2023-12-09_17-53-43.csv"

    tmp_clean_csv = clean_csv(csv_path)
    run_ledger_convert(tmp_clean_csv, csv_path)


main()

if __name__ == "__main__":

    main()
