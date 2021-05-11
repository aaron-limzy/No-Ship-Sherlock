#jupyter notebook --NotebookApp.iopub_data_rate_limit=1.0e10
import pandas as pd
import numpy as np
import datetime

import matplotlib
import cufflinks as cf
import plotly
import plotly.offline as py
import plotly.graph_objs as go
import plotly.express as px

import os
#pip install chart_studio



pd.set_option('display.max_columns', None)
#pd.options.plotting.backend = "plotly"

# Returns a Pandas df of the Shipment details.
def get_shipment_routes(excel_route_file):
    xls = pd.ExcelFile(excel_route_file)
    df_ship_routes = pd.read_excel(xls,"MasterData" )
    #xls = [] # Free up resource
    print("Length of Excel: {}".format(len(df_ship_routes)))
    df_ship_routes.head()
    # Check that there are no duplicates
    sum(df_ship_routes['Route'].duplicated())
    #df_ship_routes = df_ship_routes['Mode'].str.lower() == "air"
    print("The count of mode by air: {}".format(sum(df_ship_routes['Mode'].str.lower() == "ocean")))
    return df_ship_routes

# Read in the shipment data from the file.
def get_shipment_data(excel_ship_file):
    #print("Excel File Name: {}".format(excel_ship_file))
    df_ship_data = pd.read_csv(excel_ship_file)
    print("Excel File Name: {} | File shape is: {}".format(excel_ship_file, df_ship_data.shape))
    return df_ship_data


# -------- Data Cleaning Procedures. -------

# Cast to datetime.
def column_to_datetime(df):
    col_to_datetime = ['Departed from Origin Port Milestone Local Time',
                       'Departed from Origin Port Milestone Time',
                       'Departed from Origin Port Milestone Received Time',
                       'Arrived at Destination Port Milestone Local Time',
                       'Arrived at Destination Port Milestone Time',
                       'Arrived at Destination Port Milestone Received Time',
                       'Est. Arrival at Destination Port Milestone Local Time',
                       'Est. Arrival at Destination Port Milestone Time',
                       'Est. Arrival at Destination Port Milestone Received Time']

    for col in col_to_datetime:
        # df = df[df[c].notnull()] # Want to get rid of all the null values.

        print("Changing Column '{}' to datetime.".format(col))
        df[col] = pd.to_datetime(df[col], format='%Y-%m-%d %H:%M:%S')

    return df

# Want to get the stats for the difference between two columns
def get_stats_recieved_vs_actual(df, milestone_recieved, milestone_time):
    milestone_recieved_year = pd.DatetimeIndex(df[milestone_recieved]).year
    milestone_recieved_month = pd.DatetimeIndex(df[milestone_recieved]).month

    print(f"Recieved Year: {list(milestone_recieved_year.unique())}")
    print(f"Recieved Month : {list(milestone_recieved_month.unique())}")

    print("\n")
    print(f"The summary of '{milestone_recieved}' - '{milestone_time}'")
    timediff = (df[milestone_recieved] - df[milestone_time]).dt.days
    print(timediff[timediff.notna()].describe().apply(lambda x: format(x, ',.2f')))

    return

# Will be used to correct all the recieved/actual time that has year issues.
def correct_milestone_actual_timediff(df_original, milestone_recieved, milestone_time, check_days, correction_days):
    df = df_original.copy()
    df[milestone_time] = df[milestone_time].mask((df[milestone_recieved] - df[milestone_time]).dt.days > check_days, \
                                                 df[milestone_time] + pd.to_timedelta(correction_days, unit='D'))

    return df


# Will be used to correct all the recieved/actual time that has year issues.
# This function are for those that are negative.
def correct_negative_milestone_actual_timediff(df_original, milestone_recieved, milestone_time, check_days,
                                               correction_days):
    df = df_original.copy()
    df[milestone_time] = df[milestone_time].mask((df[milestone_recieved] - df[milestone_time]).dt.days < check_days, \
                                                 df[milestone_time] - pd.to_timedelta(correction_days, unit='D'))
    return df


def wrongyear_data_cleaning(df):
    # ---------------- Correction of timing for 2020/2021/2022 -------------------------

    # Correct Departed where it's 1 year off.
    milestone_recieved = "Departed from Origin Port Milestone Received Time"
    milestone_time = 'Departed from Origin Port Milestone Time'
    df = correct_milestone_actual_timediff(df, milestone_recieved, milestone_time, 300, 366)

    # Correct Arrived where it's 1 year off.
    milestone_recieved = "Arrived at Destination Port Milestone Received Time"
    milestone_time = 'Arrived at Destination Port Milestone Time'
    df = correct_milestone_actual_timediff(df, milestone_recieved, milestone_time, 300, 366)

    # Correct Estimated where it's 1 year off.
    milestone_recieved = "Est. Arrival at Destination Port Milestone Received Time"
    milestone_time = 'Est. Arrival at Destination Port Milestone Time'

    # Correct Estimated where it's -1 and -2 year off.
    df = correct_negative_milestone_actual_timediff(df, milestone_recieved, milestone_time, -700, 731)
    df = correct_negative_milestone_actual_timediff(df, milestone_recieved, milestone_time, -300, 366)

    # df = correct_negative_milestone_actual_timediff(df, milestone_recieved, milestone_time, -150, 150)
    # 1) Correct by ID Based on Eyeball. BL = 580041033000
    # 2) Don't do it.

    df = correct_milestone_actual_timediff(df, milestone_recieved, milestone_time, 300, 366)

    #     #Change Arrived at destination port year from 2020 to 2021 when ATA time - ATA received time < -300
    #     df['Arrived at Destination Port Milestone Time'] = df['Arrived at Destination Port Milestone Time'].mask(
    #         (df['Arrived at Destination Port Milestone Received Time'] - \
    #          df['Arrived at Destination Port Milestone Time']).dt.days > 300,
    #         df['Arrived at Destination Port Milestone Time'] +  pd.to_timedelta(366, unit='D'))

    # #     df['Arrived at Destination Port Milestone Local Time'] = df['Arrived at Destination Port Milestone Local Time'].mask(
    # #         (df['Arrived at Destination Port Milestone Local Time'] - \
    # #              df['Arrived at Destination Port Milestone Time']).dt.days < -300,
    # #             df['Arrived at Destination Port Milestone Local Time'] +  pd.to_timedelta(366, unit='D'))

    #     #Change Arrived at destination port year from 2022 to 2021 when ATA time - ATA received time > 300
    #     df['Arrived at Destination Port Milestone Time'] = df['Arrived at Destination Port Milestone Time'].mask(
    #         (df['Arrived at Destination Port Milestone Time']- \
    #                          df['Arrived at Destination Port Milestone Received Time']).dt.days >= 300,
    #         df['Arrived at Destination Port Milestone Time'] -  pd.to_timedelta(366, unit='D'))

    # #     df['Arrived at Destination Port Milestone Local Time'] = df['Arrived at Destination Port Milestone Local Time'].mask(
    # #         (df['Arrived at Destination Port Milestone Local Time'] - \
    # #          df['Arrived at Destination Port Milestone Time']).dt.days > 300,
    # #         df['Arrived at Destination Port Milestone Local Time'] -  pd.to_timedelta(366, unit='D'))

    #     #Change Departed from Origin Port Milestone year from 2020 to 2021 when ATD time - ATD received time < -300
    #     df['Departed from Origin Port Milestone Time'] = df['Departed from Origin Port Milestone Time'].mask(
    #         (df['Departed from Origin Port Milestone Received Time'] - \
    #          df['Departed from Origin Port Milestone Time']).dt.days < -300,
    #         df['Departed from Origin Port Milestone Time'] +  pd.to_timedelta(366, unit='D'))

    # #     df['Departed from Origin Port Milestone Local Time'] = df['Departed from Origin Port Milestone Local Time'].mask(
    # #         (df['Departed from Origin Port Milestone Local Time'] - \
    # #          df['Departed from Origin Port Milestone Time']).dt.days < -300,
    # #         df['Departed from Origin Port Milestone Local Time'] +  pd.to_timedelta(366, unit='D'))

    #     # Change the Estimated arrival if it's more than 1 year apart.
    #     df['Est. Arrival at Destination Port Milestone Time'] = df['Est. Arrival at Destination Port Milestone Time'].mask(
    #         (df['Arrived at Destination Port Milestone Time'] - \
    #          df['Est. Arrival at Destination Port Milestone Time']).dt.days < -300,
    #         df['Est. Arrival at Destination Port Milestone Time'] -  pd.to_timedelta(366, unit='D'))

    return df


def data_cleaning(df):
    df = df[~df.duplicated()]

    # First, Want to clean up data that is obviously duplicated.
    print("Data that is duplicated exactly: {}".format(sum(df.duplicated())))

    print("Shape after dedup: {}".format(df.shape))

    # If H-K missing, replace with Latest D-G
    # [(Replacement, original)]
    replace_column = [('Onboard at Origin Port Milestone Local Time', 'Departed from Origin Port Milestone Local Time'),
                      ('Onboard at Origin Port Milestone Time', 'Departed from Origin Port Milestone Time'),
                      ('Onboard at Origin Port Milestone Received Time',
                       'Departed from Origin Port Milestone Received Time'),
                      ('Onboard at Origin Port Milestone Source', 'Departed from Origin Port Milestone Source')]

    for (r, o) in replace_column:
        df[o] = df[o].mask(df[o].isna(), df[r])
        # df =  replace_original_if_null(df=df, original=o, replacement=r)

    print("Shape after replacement: {}".format(df.shape))

    # Cast to datetime.
    #     col_to_datetime = ['Departed from Origin Port Milestone Local Time',
    #        'Departed from Origin Port Milestone Time',
    #        'Departed from Origin Port Milestone Received Time',
    #        'Arrived at Destination Port Milestone Local Time',
    #        'Arrived at Destination Port Milestone Time',
    #        'Arrived at Destination Port Milestone Received Time',
    #        'Est. Arrival at Destination Port Milestone Local Time',
    #        'Est. Arrival at Destination Port Milestone Time',
    #        'Est. Arrival at Destination Port Milestone Received Time']

    #     for col in col_to_datetime:
    #         #df = df[df[c].notnull()] # Want to get rid of all the null values.

    #         print("Changing Column '{}' to datetime.".format(col))
    #         df[col] = pd.to_datetime(df[col], format='%Y-%m-%d %H:%M:%S')

    #         #df[c] = df[c].apply(lambda x: datetime.datetime.strptime(x,'%Y-%m-%d %H:%M:%S') if not pd.isnull(x) else x)

    # Changed the needed columns to datetime.
    df = column_to_datetime(df)
    print("Shape after col_to_datetime: {}".format(df.shape))

    # Want to do the year clean up for those data with wrongly labelled years.
    df = wrongyear_data_cleaning(df)

    print("Shape after wrongyear_data_cleaning: {}".format(df.shape))

    # Remove entries where Arrival Milestone Received Time is earlier than Departure Time
    df = df[df["Departed from Origin Port Milestone Time"] < df["Arrived at Destination Port Milestone Received Time"]]
    print("Shape after 1: {}".format(df.shape))

    # Remove entries where Arrival is earlier than Departure.
    df = df[df["Departed from Origin Port Milestone Time"] < df["Arrived at Destination Port Milestone Time"]]
    print("Shape after 2: {}".format(df.shape))

    # "Est. Arrival at Destination Port Milestone Received Time" < "Arrived at Destination Port Milestone Time"
    df = df[df["Est. Arrival at Destination Port Milestone Received Time"] < df[
        "Arrived at Destination Port Milestone Time"]]
    print("Shape after 3: {}".format(df.shape))

    # "Est. Arrival at Destination Port Milestone Received Time" < "Arrived at Destination Port Milestone Received Time"
    df = df[df["Est. Arrival at Destination Port Milestone Received Time"] < df[
        "Arrived at Destination Port Milestone Received Time"]]
    print("Shape after 4: {}".format(df.shape))

    ## R Later than I
    # Remove entries where Est. Arrival at Destination Port Milestone Received Time is later than Arrived at Destination Port Milestone Time.
    # "Est. Arrival at Destination Port Milestone Received Time" > "Departed from Origin Port Milestone Time"
    df = df[df["Departed from Origin Port Milestone Time"] < df["Est. Arrival at Destination Port Milestone Time"]]
    print("Shape after 5: {}".format(df.shape))

    # Sort by Latest M, Take earliest R
    # "Arrived at Destination Port Milestone Time"
    # "Est. Arrival at Destination Port Milestone Received Time"
    df.sort_values(
        ["Arrived at Destination Port Milestone Time", "Est. Arrival at Destination Port Milestone Received Time"], \
        ascending=[False, True], inplace=True)

    print("Shape after 6: {}".format(df.shape))

    # df = df[~df.duplicated()]

    # Drop the duplicated Shipment IDs.
    # Want the First ones, since we have sorted it already
    df.drop_duplicates(subset=['Shipment id'], keep='first', inplace=True)
    print("Shape after 7: {}".format(df.shape))

    return df

