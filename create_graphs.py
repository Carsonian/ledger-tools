import pandas as pd
import sqlite3
import plotly.express as px
from dash import Dash, html, dash_table, dcc, callback, Output, Input


def get_sqlite_data(database_name):
    # Create connection
    cnx = sqlite3.connect(database_name)

    # Read the data into dfs
    trans_df = pd.read_sql_query("SELECT * FROM ledger_expenses", cnx)
    nights_df = pd.read_sql_query("SELECT * FROM city_nights", cnx)

    return trans_df, nights_df


def transform_data(trans_df, nights_df, per_day):
    # Filter out revalued and adjustment transactions
    trans_df = trans_df[~trans_df['Category'].str.contains("<Revalued>|<Adjustment>")]

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

    return sorted_df


def make_bar_graph(df, cities_order, use_trip_order, use_per_day):

    # Create the bar chart  ----------------------
    fig = px.bar(df,
                 x='City', y=["Amount"],
                 color='Category',
                 category_orders={"Category": 'total_descending'},
                 hover_data={'value': ':.2r'})

    # If trip order, sort the cities by the trip order
    if use_trip_order:
        fig.update_layout(xaxis={'categoryorder': 'array',
                                 'categoryarray': cities_order})
    else:
        fig.update_layout(xaxis={'categoryorder': 'total descending'})

    # If per day, add constant line at $65 per day and new title
    if use_per_day:
        fig.add_hline(y=65)
        fig.update_layout(title="Per Day Expenses by City.")
    else:
        fig.update_layout(title="Total Expenses by City.")

    # Style the chart
    fig.update_layout(font={'size': 18})
    fig.update_xaxes(tickangle=315)

    return fig


def make_specific_chart(country_or_city, name, chart_type, trans_df, nights_df, per_day, trip_order):
    """Make a chart for data on just one Country or City, can be bar, pie, or table"""


def main():

    database_name = 'expenses.db'
    trans_df, nights_df = get_sqlite_data(database_name)

    # Get a df for totals and per day values
    totals_df = transform_data(trans_df, nights_df, per_day=False)
    per_day_df = transform_data(trans_df, nights_df, per_day=True)

    # Get list of cities in trip order
    cities_trip_order = nights_df['City'].to_list()

    bar_fig = make_bar_graph(per_day_df, cities_trip_order,
                             use_trip_order=True, use_per_day=True)

    # Dash app ############################################

    app = Dash(__name__)

    # App layout
    app.layout = html.Div([
        # Title
        html.Div(children='Asia Trip Expenses Report',
                 style={'textAlign': 'center', 'color': 'black', 'fontSize': 30}),
        html.Hr(),

        # Section containing the order and total selectors
        html.Div(className='row', style={'text-align': 'center'}, children=[
            dcc.RadioItems(options=['Trip Order', 'Descending Order'],
                           value='Trip Order', id='order-picker',
                           style={'display': 'inline-block',
                                  'text-align': 'left',
                                  'width': '180px',
                                  'border': '2px solid black',
                                  'padding': '8px',
                                  'margin': '8px'}),
        
            dcc.RadioItems(options=['Per Day Costs', 'Total Costs'],
                           value='Per Day Costs', id='per-day-picker',
                           style={'display': 'inline-block',
                                  'text-align': 'left',
                                  'width': '180px',
                                  'border': '2px solid black',
                                  'padding': '8px',
                                  'margin': '8px'}),
                                  
        ]),
        
        # Bar chart
        html.Div(className='row', children=[
            dcc.Graph(figure=bar_fig, id='bar_fig',
                      style={'height': '90vh', 'fontSize': 16}),
        ]),
    ])

    # Setup the interaction for the order picker
    @callback(
        Output(component_id='bar_fig', component_property='figure'),
        [Input(component_id='order-picker', component_property='value'),
         Input(component_id='per-day-picker', component_property='value')]
    )
    # Set how to update the graph
    def update_graph(order_chosen, total_chosen):
        if order_chosen == 'Trip Order':
            chosen_trip_order = True
        else:
            chosen_trip_order = False
        if total_chosen == 'Per Day Costs':
            bar_fig = make_bar_graph(per_day_df, cities_trip_order,
                                     use_trip_order=chosen_trip_order,
                                     use_per_day=True)
        else:
            bar_fig = make_bar_graph(totals_df, cities_trip_order,
                                     use_trip_order=chosen_trip_order,
                                     use_per_day=False)

        return bar_fig

    app.run()


main()

if __name__ == "__main__":
    main()
