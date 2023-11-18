import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, html, dash_table, dcc, callback, Output, Input
from datetime import datetime


def get_sqlite_data(database_name):
    # Create connection
    cnx = sqlite3.connect(database_name)

    # Read the data into dfs
    trans_df = pd.read_sql_query("SELECT * FROM ledger_expenses", cnx)
    nights_df = pd.read_sql_query("SELECT * FROM city_nights", cnx)

    return trans_df, nights_df


def transform_data(trans_df, nights_df, per_day, city_or_country):
    # Filter out revalued and adjustment transactions
    trans_df = trans_df[~trans_df['Category'].str.contains("<Revalued>|<Adjustment>")]

    # Group by city and category and find sum of amounts
    aggregated = trans_df.groupby([city_or_country, 'Category']) \
                         .agg({'Amount': ['sum']}) \
                         .reset_index()
    aggregated.columns = [city_or_country, 'Category', 'Amount']

    # If making per day graph, divide all amounts by days in that city
    if per_day:
        # Create a column of nights spent
        aggregated = pd.merge(aggregated, nights_df, on=city_or_country, how='left')

        # Divide the amount column by the nights column
        aggregated['Amount'] = aggregated['Amount']/aggregated['Nights']

        # Round again
        aggregated['Amount'] = aggregated['Amount'].round(decimals=2)

    # Sort the categories by a manual list -----------------------------
    try:
        sorter = ['Accomodation', 'Food & Drink', 'Activities',
                  'Transportation:Plane', 'Transportation:Boat',
                  'Transportation:Bus', 'Transportation:Train',
                  'Transportation:City Transit', 'Untracked Cash',
                  'ATM Fees', 'Visa Fees', 'Insurance', 'Purchases', 'Misc']

        sorted_df = aggregated.sort_values(by="Category",
                                           key=lambda column: column.map(lambda e: sorter.index(e)))
    except ValueError:
        # If there are values not in the manual list, sort by the total sum instead
        # Sort the categories by largest total amount ----------------------
        # https://stackoverflow.com/questions/14941366/
        # pandas-sort-by-group-aggregate-and-column
        print('Error in manual sorting, sorting categories automatically by sum')

        # Group by category and sort by sum of amount
        grp = aggregated.groupby('Category')
        grp[['Amount']].transform(sum).sort_values('Amount', ascending=False)

        # Sort the aggregated by the indexes we got from the sort above
        sorted_df = aggregated.iloc[grp[['Amount']].transform(sum)
                                    .sort_values('Amount', ascending=False).index]

    return sorted_df


def make_bar_graph(df, cities_order, use_trip_order, use_per_day, city_or_country):

    # Filter out international transactions
    df = df[~df[city_or_country].str.contains("International", na=False)]

    # Create the bar chart  ----------------------
    fig = px.bar(df,
                 x=city_or_country, y=["Amount"],
                 color='Category',
                 color_discrete_map=category_color_dict,
                 category_orders={"Category": 'total_descending'},
                 )

    # If trip order, sort the cities by the trip order
    if use_trip_order:
        fig.update_layout(xaxis={'categoryorder': 'array',
                                 'categoryarray': cities_order})
    else:
        fig.update_layout(xaxis={'categoryorder': 'total descending'})

    # If per day, add constant line at $65 per day and new title
    if use_per_day:
        fig.add_hline(y=65)
        fig.update_layout(title="Per Day Expenses by City")
    else:
        fig.update_layout(title="Total Expenses by City")

    # Style the chart
    fig.update_layout(font={'size': 18})
    fig.update_layout(yaxis_tickprefix='$')
    fig.update_xaxes(tickangle=315)

    return fig


def make_specific_chart(use_country_or_city, name, chart_type, trans_df, nights_df, per_day):
    """Make a chart for data on just one Country or City, can be bar, pie, or table"""

    # Filter out revalued and adjustment transactions
    trans_df = trans_df[~trans_df['Category'].str.contains("<Revalued>|<Adjustment>")]

    # Filter the df to only the values for the specific country or city
    trans_df = trans_df.loc[trans_df[use_country_or_city] == name]

    # If making per day graph, divide all amounts by days in that city
    if per_day:
        # Get the days spent in the city
        nights = nights_df.loc[nights_df[use_country_or_city] == name, 'Nights'].iloc[0]

        # Divide the amount column by the nights spend
        trans_df['Amount'] = trans_df['Amount']/nights

    if chart_type == 'bar':
        # Create the bar chart  ----------------------
        fig = px.bar(trans_df,
                     x='Category', y=["Amount"],
                     color='Category',
                     category_orders={"Category": 'total_descending'},
                     )

        fig.update_xaxes(tickangle=315)

        # If per day, add constant line at $65 per day and new title
        if per_day:
            fig.add_hline(y=65)

    if chart_type == 'pie':
        # Create the pie chart
        fig = px.pie(trans_df,
                     values='Amount', names='Category',
                     )

    # If per day, add constant line at $65 per day and new title
    if per_day:
        fig.update_layout(title="Per Day Expenses by in " + name)
    else:
        fig.update_layout(title="Total Expenses in " + name)

    # Style the chart
    fig.update_layout(font={'size': 18})

    return fig


def make_total_graphs(city_or_country, df):
    """Make charts to show total amount spent"""

    if city_or_country is None:
        fig = px.pie(df,
                     values='Amount', names='Category',
                     )
    elif city_or_country == 'City':
        fig = px.pie(df,
                     values='Amount', names='City',
                     )
    elif city_or_country == 'Country':
        fig = px.pie(df,
                     values='Amount', names='Country',
                     )
    else:
        print('Invalid city or country value, use "City", "Country" or None')

    fig.update_layout(title="Total Expenses.")

    # Style the chart
    fig.update_layout(font={'size': 18})
    fig.update_traces(hoverinfo='label+percent', textinfo='value')
    return fig


def make_category_bar(df):
    """Make bar chart to show total amount spent per category"""

    # Filter out revalued and adjustment transactions
    df = df[~df['Category'].str.contains("<Revalued>|<Adjustment>")]

    # Group by city and category and find sum of amounts
    df = df.groupby('Category').sum('Amount').reset_index()

    # Sort by sum descending
    df = df.sort_values(by=['Amount'], ascending=False)

    fig = px.bar(df,
                 x='Category', y=["Amount"],
                 color='Category',
                 color_discrete_map=category_color_dict,
                 )

    fig.update_layout(title="Total Expenses by Category")

    # Style the chart
    fig.update_layout(font={'size': 18})
    return fig


def make_gauge(df):
    """Make a gauge chart of the total spent"""

    df['Date'] = pd.to_datetime(df['Date'])

    df = df.groupby(df['Date'].dt.strftime('%y-%m-%d'))['Amount'].sum().reset_index()

    df["cum_sum"] = df["Amount"].cumsum()
    df = df.sort_index()

    # Get current total
    current_total = df["cum_sum"].iloc[-1]

    # Find total days since trip start date
    most_recent_date = datetime.strptime(df["Date"].iloc[-1], '%y-%m-%d')
    trip_start_date = datetime.strptime('2023-06-21', '%Y-%m-%d')
    days_so_far = (most_recent_date - trip_start_date).days
    months_so_far = (most_recent_date.month - trip_start_date.month)

    day_expenses = current_total / days_so_far
    month_expenses = current_total / months_so_far

    # Make reference expenses of 65 dollars a day
    reference_expenses = 65*days_so_far

    # Create the total expenses indicator
    fig = go.Figure(go.Indicator(
        mode = "number+delta",
        value = current_total,
        number = {"prefix": "$"},
        delta = {"reference": reference_expenses, "prefix": "$", },
        title = {"text": "Total Expenses"},
        domain = {'x': [0, 0], 'y': [0.5, 1]}))

    # Add per month 
    fig.add_trace(go.Indicator(
    mode = "number",
    value = month_expenses,
    number = {"prefix": "$", 'font': {'size': 65}},
    title = {"text":
             f"Per Month<br><span style='font-size:1em;color:gray'>({months_so_far} Months)</span><br><span style='font-size:1em;color:gray'>"},
    domain = {'x': [0.7, 1], 'y': [0.1, 0.3]}))

    # Add per day
    fig.add_trace(go.Indicator(
    mode = "number",
    value = day_expenses,
    number = {"prefix": "$", 'font': {'size': 65}},
    title = {"text":
             f"Per Day<br><span style='font-size:1em;color:gray'>({days_so_far} Days)</span><br><span style='font-size:1em;color:gray'>"},
    domain = {'x': [0.4, 1], 'y': [0.1, 0.3]}))
        
    # Add line graph of running total
    # pop the rows before june so it looks better
    after_june_df = df[(df['Date'] > '23-06-21')]
    fig.add_trace(go.Scatter(y = after_june_df['cum_sum'], x=after_june_df['Date']))

    return fig


category_color_dict = {'Accomodation': '#3366CC', 
                       'Food & Drink': '#DC3912',
                       'Activities': '#FF9900',
                       'Transportation:Plane': '#109618',
                       'Transportation:Boat':'#0099C6',
                       'Transportation:Bus':'#B82E2E',
                       'Transportation:Train':'#EECA3B',
                       'Transportation:City Transit':'#DD4477',
                       'Untracked Cash': '#66AA00',
                       'ATM Fees': '#990099',
                       'Purchases': '#316395',
                       'Misc': '#8C564B'
                       }


def main():

    print(px.colors.qualitative.G10)

    database_name = 'expenses.db'
    trans_df, nights_df = get_sqlite_data(database_name)

    trans_df['Amount'] = trans_df['Amount'].round(decimals=2)

    # Get a df for city totals and per day values
    city_totals_df = transform_data(trans_df, nights_df,
                                    per_day=False, city_or_country='City')
    city_per_day_df = transform_data(trans_df, nights_df,
                                     per_day=True, city_or_country='City')

    # Get a df for country totals and per day values
    country_totals_df = transform_data(trans_df, nights_df,
                                       per_day=False, city_or_country='Country')
    country_per_day_df = transform_data(trans_df, nights_df,
                                        per_day=True, city_or_country='Country')


    # Get list of cities in trip order
    cities_trip_order = nights_df['City'].to_list()
    cities_trip_order = [i for i in cities_trip_order if i is not None]
    cities_trip_order.remove('International')

    # Get list of countries in trip order
    country_trip_order = nights_df['Country'].to_list()
    country_trip_order = [i for i in country_trip_order if i is not None]

    bar_fig = make_bar_graph(city_per_day_df, cities_trip_order,
                             use_trip_order=True, use_per_day=True,
                             city_or_country='City')

    spec_chart = make_specific_chart('City', 'Da Lat', 'pie',
                                     trans_df, nights_df, per_day=True)

    total_chart = make_total_graphs('Country', country_totals_df)

    cat_bar_fig = make_category_bar(trans_df)

    gauge_chart = make_gauge(trans_df)

    # Dash app ############################################

    app = Dash(__name__)

    # App layout
    app.layout = html.Div([
        # Title
        html.Div(children='Asia Trip Expenses Report',
                 style={'textAlign': 'center', 'color': 'black', 'fontSize': 30}),
        html.Hr(),

        # Gauge Chart
        html.Div(className='row', children=[
            dcc.Graph(figure=gauge_chart, id='gauge_fig',
                      style={'height': '90vh', 'fontSize': 16}),
        ]),

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

            dcc.RadioItems(options=['City', 'Country'],
                           value='City', id='city-country-picker',
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

        # Category Bar chart
        html.Div(className='row', children=[
            dcc.Graph(figure=cat_bar_fig, id='cat_bar_fig',
                      style={'height': '90vh', 'fontSize': 16}),
        ]),

        # Specific chart
        html.Div(className='row', children=[
            dcc.Graph(figure=total_chart, id='total_chart_fig',
                      style={'height': '90vh', 'fontSize': 16}),
            ]),
        

        # Specific chart
        html.Div(className='row', children=[
            dcc.Graph(figure=spec_chart, id='spec_chart_fig',
                      style={'height': '90vh', 'fontSize': 16}),
            ]),
        
    ])

    # Setup the interaction for the order picker
    @callback(
        Output(component_id='bar_fig', component_property='figure'),
        [Input(component_id='order-picker', component_property='value'),
         Input(component_id='per-day-picker', component_property='value'),
         Input(component_id='city-country-picker', component_property='value')]
        
    )
    # Set how to update the graph
    def update_graph(order_chosen, total_chosen, location_chosen):
        if order_chosen == 'Trip Order':
            chosen_trip_order = True
        else:
            chosen_trip_order = False
        if total_chosen == 'Per Day Costs':
            per_day = True
        else:
            per_day = False
        if location_chosen == 'City':
            order = cities_trip_order
            if per_day:
                df_to_use = city_per_day_df
            else:
                df_to_use = city_totals_df
        else:
            order = country_trip_order
            if per_day:
                df_to_use = country_per_day_df
            else:
                df_to_use = country_totals_df

        bar_fig = make_bar_graph(df_to_use,
                                 order,
                                 use_trip_order=chosen_trip_order,
                                 use_per_day=per_day,
                                 city_or_country=location_chosen)

        return bar_fig

    app.run()


main()

if __name__ == "__main__":
    main()
