import pandas as pd
import sqlite3
import plotly.express as px
from dash import Dash, dcc, html, Input, Output


def get_sqlite_data(database_name):
    # Create connection
    cnx = sqlite3.connect(database_name)

    # Read the data into dfs
    trans_df = pd.read_sql_query("SELECT * FROM ledger_expenses", cnx)
    nights_df = pd.read_sql_query("SELECT * FROM city_nights", cnx)

    return trans_df, nights_df


def make_bar_graphs(trans_df, nights_df, per_day, trip_order):

    # Filter out revalued and adjustment transactions
    trans_df = trans_df[~trans_df['Category'].str.contains("<Revalued>|<Adjustment>")]

    # Get list of cities in trip order
    cities_trip_order = nights_df['City'].to_list()

    # Group by city and category and find sum of amounts
    aggregated = trans_df.groupby(['City', 'Category']) \
                         .agg({'Amount': ['sum']}) \
                         .reset_index()
    aggregated.columns = ['City', 'Category', 'Amount']

    # If making per day graph, divide all amounts by days in that city
    if per_day:
        # Create a column of nights spent
        aggregated = pd.merge(aggregated, nights_df, on='City', how='left')
        
        # Divide the amount column by the nights column
        aggregated['Amount'] = aggregated['Amount']/aggregated['Nights']

    # Sort the categories by a manual list -----------------------------
    try:
        sorter = ['Accomodation', 'Food & Drink', 'Activities', 'Transportation:Plane', 'Transportation:Boat',
                  'Transportation:Bus', 'Transportation:Train', 'Transportation:City Transit',
                  'Untracked Cash', 'ATM Fees', 'Visa Fees', 'Insurance', 'Purchases', 'Misc']

        sorted_df = aggregated.sort_values(by="Category",
                                           key=lambda column: column.map(lambda e: sorter.index(e)))
    except ValueError:
        # If there are values not in the manual list, sort by the total sum instead
        # Sort the categories by largest total amount ----------------------
        # https://stackoverflow.com/questions/14941366/
        # pandas-sort-by-group-aggregate-and-column

        # Group by category and sort by sum of amount
        grp = aggregated.groupby('Category')
        grp[['Amount']].transform(sum).sort_values('Amount', ascending=False)

        # Sort the aggregated by the indexes we got from the sort above
        sorted_df = aggregated.iloc[grp[['Amount']].transform(sum)
                                    .sort_values('Amount', ascending=False).index]


    # Create the bar chart  ----------------------
    fig = px.bar(sorted_df,
                 x='City', y=["Amount"],
                 color='Category',
                 category_orders={"Category": 'total_descending'},
                 hover_data={'value': ':.2r'},
                 title="Expenses per city.")

    # If trip order, sort the cities by the trip order
    if trip_order:
        fig.update_layout(xaxis={'categoryorder': 'array',
                                 'categoryarray': cities_trip_order})
    else:
        fig.update_layout(xaxis={'categoryorder': 'total descending'})

    # If per day, add constant line at $65 per day and new title
    if per_day:
        fig.add_hline(y=65)
        fig.update_layout(title="Expenses per city per day.")

    fig.show()


def main():

    database_name = 'expenses.db'
    trans_df, nights_df = get_sqlite_data(database_name)

    make_bar_graphs(trans_df, nights_df, per_day=True, trip_order=True)


main()
if __name__ == "__main__":
    main()


# Dash stuff for later ###########################################
    # app = Dash(__name__)

    # app.layout = html.Div([
    #     html.H4('Expenses per city per day.'),
    #     dcc.Dropdown(
    #         id="dropdown",
    #         options=["Fri", "Sat", "Sun"],
    #         value="Fri",
    #         clearable=False,
    #     ),
    #     dcc.Graph(id="graph"),
    # ])

    # @app.callback(
    #     Output("graph", "figure"), 
    #     Input("dropdown", "value"))
    # def update_bar_chart(day):
    #     df = trans_df
    #     mask = df["day"] == day
    #     fig = px.bar(df[mask], x="sex", y="total_bill", 
    #                  color="smoker", barmode="group")
    #     return fig

    # app.run_server(debug=True)
