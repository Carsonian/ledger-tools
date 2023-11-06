import pandas as pd
import matplotlib.pyplot as plt
from tabulate import tabulate

import tomllib
import os
from io import StringIO
import subprocess
# import argparse


def get_ledger_report(ledger_file):
    """Run the ledger balance report on a ledger file
    and return the output as a string"""

    report_cmd = r"ledger -f " + ledger_file \
                 + r" bal -X $ ^expenses --pivot City --balance-format '%A:%T\n'"

    # Get the ledger csv output as a string
    report_output = subprocess.check_output(report_cmd, shell=True).decode('utf-8')

    return report_output


def make_df_from_report(report):
    """Create a pandas df from the report string"""

    report_lines = report.splitlines()

    expenses_list = []
    for line in report_lines:
        # Split each line into the seperate account values
        values = line.split(':')
        count = 0
        value_list = []
        for value in values:
            if value.startswith('$'):
                # If its the final $ entry but not the 5th column yet
                # fill with null until on the 5th column
                while count < 5:
                    value_list.append(None)
                    count += 1
            if value == 'Expenses' and count == 0:
                # If expenses is the first value
                # append a null and no city first
                value_list.append(None)
                value_list.append('No City')
                count += 2
            value_list.append(value)
            count += 1
        expenses_list.append(value_list)

    # Turn the list into a df
    transaction_df = pd.DataFrame(expenses_list)
    return transaction_df


def clean_and_format_df(df):
    """Choose and rename columns, replace none with totals,
    convert currency to float"""

    # Remove unnecessary columns and rename the rest
    df.drop(df.columns[[0, 2]], axis=1, inplace=True)
    df.columns = ["City", "Category", "Sub-Category", "Amount"]

    # Na values in City and Category are totals
    df[['City', 'Category']] = \
        df[['City', 'Category']].fillna('Total')

    # Turn currency string into float data
    df['Amount'] = df['Amount'].replace('[\$,]', '', regex=True).astype(float)

    subs_df = df.copy(deep=True)

    # Pivot the df so there's 1 row per city, with all categories as columns
    df = pd.pivot_table(df, index='City', columns=["Category"], values="Amount")
    df = df.reset_index()

    # Create another pivot df with the subcategories
    subs_df = pd.pivot_table(subs_df, index='City', columns=["Category", "Sub-Category"], values="Amount")
    subs_df.columns = subs_df.columns.map('_'.join)
    subs_df = subs_df.reset_index()
    
    # Merge the two dfs
    df = pd.merge(df, subs_df, how='left')

    # Remove the index name
    df = df.rename_axis(None, axis=1)

    return df


def read_days_toml(days_toml):
    """Read the toml file to a list, fix place names, export to sqlite"""

    with open(days_toml, "rb") as f:
        nights_data = tomllib.load(f)['Nights']

    # Replace - with a space in city names
    nights_data = {k.replace('-', ' '): v for (k, v) in nights_data.items()}

    return nights_data


def make_per_day_df(df, nights_data):
    """Divide all amount values in the df by the amount of night spent in that city"""

    # Create a column of nights spent
    df['nights'] = df['City'].map(nights_data)

    # Get a list of the amount columns
    amount_cols = df.drop(['City', 'nights'], axis=1)
    amount_cols = list(amount_cols.columns.values)

    # Divide the amount columns by the nights column
    df.loc[:, amount_cols] = df.loc[:, amount_cols].div(df['nights'], axis=0)

    return df


def stacked_bar_report(df):

    # Sort by total row before removing it
    df = df.set_index('City')
    df = df.sort_values(by='Total', ascending=False, axis=1)
    df = df.reset_index()

    # Remove total and nocity city values
    df = df[~df['City'].isin(['Total', 'No City', 'Transit'])]

    # Remove transportation subcategories to avoid doubling amounts
    df = df.drop(['Transportation_Train', 'Transportation_Plane', 'Transportation_Bus', 'Transportation_Boat', 'Transportation_City Transit', 'Activities_Tour'], axis=1)

    # Drop transportation to avoid doubling with subcategories
    #df = df.drop('Transportation', axis=1)
    
    # Drop activities_tour to avoid doubling with subcategories
    #df = df.drop('Activities_Tour', axis=1)

    df = df.sort_values('Total', ascending=False, axis=0)

    #df.plot.bar(stacked=True, x='City', y='Total')

    df = df.drop('Total', axis=1)

    colors = ['#e6194b', '#3cb44b', '#ffe119', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe', '#008080', '#e6beff', '#9a6324', '#fffac8', '#800000', '#aaffc3', '#808000', '#ffd8b1', '#000075', '#808080', '#ffffff', '#000000']

    try:
        df.drop('nights', axis=1).plot.bar(stacked=True, x='City', color=colors).axhline(y=65, color='k', linestyle='-')
    except KeyError:
        df.plot.bar(stacked=True, x='City')


def create_report(expenses_df, per_day_df):
    """Make a report from the expenses_df and per_day_df"""

    stacked_bar_report(per_day_df)
    #stacked_bar_report(expenses_df)
    plt.show()



def main():

    ledger_file = "/home/carson/Files/accounting/asia-trip.ledger"
    days_toml = "/home/carson/Files/accounting/city-days-asia-trip.toml"

    csv_output = '/home/carson/Files/expenses.csv'

    report = get_ledger_report(ledger_file)

    expenses_df = make_df_from_report(report)

    expenses_df = clean_and_format_df(expenses_df)

    nights_data = read_days_toml(days_toml)

    per_day_df = make_per_day_df(expenses_df.copy(deep=True), nights_data)

    create_report(expenses_df, per_day_df)
    

    # Setup argparse for getting command line arguments
    # parser = argparse.ArgumentParser(
    # description='Cleanup a csv file for conversion to a ledger file.')
    # parser.add_argument('filepath')
    # args = parser.parse_args()

    # Get the csv file path from the command line argument
    # csv_path = (args.accumulate(args.filepath))


main()

if __name__ == "__main__":

    main()
