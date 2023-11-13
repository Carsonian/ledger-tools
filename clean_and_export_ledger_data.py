import pandas as pd
import sqlite3

import tomllib
from io import StringIO
import subprocess
# import argparse


def get_ledger_csv(ledger_file, output_path):
    """Get a csv file of all ledger expenses transactions and clean it."""

    # Run the ledger csv command with the format string specifying output
    format_string_csv = ''' ' %(quoted(date))␟ %(quoted(payee))␟ %(quoted(display_account))␟ %(quoted(quantity(scrub(display_amount))))␟ %(quoted(join(note | xact.note)))\n' '''

    report_cmd = r'ledger -f /home/carson/Files/accounting/asia-trip.ledger csv -X $ ^Expenses'

    report_cmd = report_cmd + ' --csv-format ' + format_string_csv

    # Run the command and turn the output into a df
    csv_output = subprocess.check_output(report_cmd, shell=True).decode('utf-8')
    transaction_df = pd.read_csv(StringIO(csv_output), sep='␟', header=None, engine='python')
    transaction_df.columns = ['Date', 'Payee', 'Category', 'Amount', 'metadata']

    # Trim quotes off both ends of all columns
    transaction_df[transaction_df.columns] = transaction_df.apply(lambda x: x.str.strip())
    transaction_df[transaction_df.columns] = transaction_df.apply(lambda x: x.str.lstrip('"'))
    transaction_df[transaction_df.columns] = transaction_df.apply(lambda x: x.str.rstrip('"'))

    # Replace all \n with real newline characters then split on them
    transaction_df['metadata'] = transaction_df['metadata'].str.replace('\\n', '\n')

    metadata_df = pd.DataFrame(columns=['Note', 'Country', 'City'])
    metadata_df[['Note', 'Country', 'City']] = transaction_df['metadata'].str.split('\n', expand=True)

    transaction_df = transaction_df.drop('metadata', axis=1)

    # Strip quotes and spaces off all metadata columns
    # Must strip whitespace, then quotes then whitespace again
    metadata_df[metadata_df.columns] = metadata_df.apply(lambda x: x.str.strip())
    metadata_df[metadata_df.columns] = metadata_df.apply(lambda x: x.str.strip('"'))
    metadata_df[metadata_df.columns] = metadata_df.apply(lambda x: x.str.strip())

    # Find the rows without notes, shift them one to the right
    no_note_rows = metadata_df.loc[metadata_df['Note']
                                   .str.startswith('City:', na=False)]
    no_note_rows = no_note_rows.shift(1, axis=1)
    metadata_df.loc[no_note_rows.index] = no_note_rows

    # Do it again for ones starting with Country:
    no_note_rows = metadata_df.loc[metadata_df['Note']
                                   .str.startswith('Country:', na=False)]
    no_note_rows = no_note_rows.shift(1, axis=1)
    metadata_df.loc[no_note_rows.index] = no_note_rows
    
    # Find the rows where city is in the country column, swap them
    rows_to_swap = metadata_df.loc[metadata_df['Country']
                                   .str.startswith('City:', na=False)]
    rows_to_swap[['City', 'Country']] = rows_to_swap[['Country', 'City']]
    metadata_df.loc[rows_to_swap.index] = rows_to_swap

    # Concat the metadata_df onto the transaction_df
    transaction_df = pd.concat([transaction_df, metadata_df],
                               axis=1)

    # Remove the City: Country: and Expenses: prefixes
    transaction_df['City'] = transaction_df['City'].str.lstrip('City')
    transaction_df['City'] = transaction_df['City'].str.lstrip(':')
    transaction_df['City'] = transaction_df['City'].str.strip()

    transaction_df['Country'] = transaction_df['Country'].str.lstrip('Country')
    transaction_df['Country'] = transaction_df['Country'].str.lstrip(':')
    transaction_df['Country'] = transaction_df['Country'].str.strip()

    transaction_df['Category'] = transaction_df['Category'].str.lstrip('Expenses')
    transaction_df['Category'] = transaction_df['Category'].str.lstrip(':')
    transaction_df['Category'] = transaction_df['Category'].str.strip()

    # Change the dtypes on date and amount
    transaction_df['Date'] = pd.to_datetime(transaction_df['Date'])
    transaction_df['Amount'] = pd.to_numeric(transaction_df['Amount'])

    return transaction_df

def read_days_toml(days_toml):
    """Read the toml file to a list, fix place names, export to sqlite"""

    with open(days_toml, "rb") as f:
        toml_file = tomllib.load(f)
        city_data = toml_file['City']
        country_data = toml_file['Country']

    # Replace - with a space in city names
    city_data = {k.replace('-', ' '): v for (k, v) in city_data.items()}
    country_data = {k.replace('-', ' '): v for (k, v) in country_data.items()}

    # Turn into a df
    city_df = pd.DataFrame(city_data.items(), columns=['City', 'Nights'])
    country_df = pd.DataFrame(country_data.items(), columns=['Country', 'Nights'])

    # Combine into nights_df
    nights_df = pd.concat([city_df, country_df])

    # Set nights to numeric
    nights_df['Nights'] = pd.to_numeric(nights_df['Nights'])

    return nights_df


def main():

    ledger_file = "/home/carson/Files/accounting/asia-trip.ledger"
    days_toml = "/home/carson/Files/accounting/city-days-asia-trip.toml"
    csv_output = '/home/carson/Files/expenses.csv'

    df = get_ledger_csv(ledger_file, csv_output)
    # Export to sqlite
    sqliteConnection = sqlite3.connect('expenses.db')
    df.to_sql('ledger_expenses', sqliteConnection,
              if_exists="replace", index=False)

    nights_df = read_days_toml(days_toml)
    # Export to sqlite
    sqliteConnection = sqlite3.connect('expenses.db')
    nights_df.to_sql('city_nights', sqliteConnection,
                     if_exists="replace", index=False)


main()

if __name__ == "__main__":

    main()
