import streamlit as st
import pandas as pd
import plotly.express as px
import altair as alt

import os
import sqlite3
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


def make_alt_bar(df, cities_order, use_trip_order, use_per_day, city_or_country):

    # Filter out international transactions
    df = df[~df[city_or_country].str.contains("International", na=False)]

    # # Create the bar chart  ----------------------
      #            color_discrete_map=category_color_dict,
      #            category_orders={"Category": 'total_descending'},
      #            )

    
    # If per day, add constant line at $65 per day and new title
    # if use_per_day:
    #     fig.add_hline(y=65)
    #     fig.update_layout(title="Per Day Expenses by City")
    # else:
    #     fig.update_layout(title="Total Expenses by City")

    # # Style the chart
    # fig.update_layout(font={'size': 18})
    # fig.update_layout(yaxis_tickprefix='$')
    # fig.update_xaxes(tickangle=315)

    # Make a bar chart with the data
    bar_chart = alt.Chart(df
    ).transform_joinaggregate(     # Make a city total value 
    city_total ='sum(Amount)',
    groupby=[city_or_country]
    ).mark_bar().encode(  # Create the chart encodings
    #x=city_or_country,
    y='Amount',
    color='Category',
    tooltip=[
        alt.Tooltip('City', title="City:  "),
        alt.Tooltip('city_total:Q', title="Total: "),
        alt.Tooltip('Category', title="Category: "),
        alt.Tooltip('Amount', title="Amount: "),
    ]
    )

    # If trip order, sort by the trip order
    if use_trip_order:
        bar_chart = bar_chart.encode(
            alt.X(city_or_country).sort(cities_order)
            )
    else:
        # Sort in descending order
        bar_chart = bar_chart.encode(
            alt.X(city_or_country).sort('descending')
            )
    

    return bar_chart


def main():

    # Get path of directory python file is in and make path for sqlite database
    dir_path = os.getcwd()
    sqlite_path = os.path.join(dir_path, 'expenses.db')

    trans_df, nights_df = get_sqlite_data(sqlite_path)

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

    ## Add a select box for choosing the chart type
    per_day_select = st.selectbox('Per Day or Totals', ['Per Day', 'Totals'])

    ## Create the chart
    if per_day_select == 'Per Day':
        bar_chart = make_alt_bar(city_per_day_df, cities_trip_order,
                                 use_trip_order=True, use_per_day=True,
                                 city_or_country='City')
    elif per_day_select == 'Totals':
        bar_chart = make_alt_bar(city_totals_df, cities_trip_order,
                                 use_trip_order=True, use_per_day=False,
                                 city_or_country='City')

    ## Display the chart
    #st.plotly_chart(bar_fig, use_container_width=True)
    #bar_chart = make_alt_bar(city_per_day_df)
    st.altair_chart(bar_chart, use_container_width=True)

    #st.bar_chart(data=city_per_day_df, x='City', y='Amount', color='Category', width=0, height=0, use_container_width=True)

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

main()
