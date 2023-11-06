from moneywallet_csv_import import *
from clean_and_export_ledger_data import *
from create_graphs import *


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


if __name__ == "__main__":

    main()

