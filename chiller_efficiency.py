import pandas as pd
import numpy as np
import math
from datetime import datetime
import requests
import matplotlib.pyplot as plt
import os
import glob
from pathlib import Path
WDPATH = Path(__file__).resolve().parent.__str__()
#.__str__()#os.getcwd()

TEST = False#True

PATH = WDPATH + '/data/'#'data/'/Users/nigarbutt/PycharmProjects/Chiller
FILE_NAME = PATH + 'data-2018-2021.xlsx'
print("\n\n\n+++++++++++++++++++++++++\n")
print(WDPATH)
print("\n\n\n+++++++++++++++++++++++++\n")
# important keys/column names
TEMPERATURE_KEY = 'Wetbulb AVG'
RUNNING_CHILLER_COUNT = 'No Running Chillers'
RT_SUM = 'Chiller RT Sum'
TIMESTAMP = 'timestamp'
DCU_POWER = 'DCP BTU Power AVG'
TOTAL_CHILLERS = 10

TES_INLET_KEY = '15_TT_01_01INPUT_VAL0'
TES_OUTLET_KEY = '15_TT_01_02INPUT_VAL0'
TES_SENSOR_FILEPATH = WDPATH+'/config'+'/TES.config'#'config/TES.config'/Users/nigarbutt/PycharmProjects/Chiller

# important modified coluumns
DAY = 'Day'
MONTH = 'Month'
HOUR = 'Hour'
MINUTE = 'Minute'
YEAR = 'Year'

MIN = 'min'
MAX = 'max'
AVG = 'avg'
FREQ = 'freq'
FULL = 'full'

CHILLER_PAIR_IDX = 0
CHILLERS_IDX = 1
EXPECTED_LOAD_IDX = 3

global BASIC_MODEL
global df
global availabilitydf
global sunset_time
global sunrise_time

sunset_time = 20 # in 24 hr formate
sunrise_time = 6 # in 24 hr formate

#New columns addes
#RT Sum (CH-01,CH-02)
#RT Sum (CH-03,CH-04)
#RT Sum (CH-05,CH-06)
#RT Sum (CH-07,CH-08)
#RT Sum (CH-09,CH-10)

def update_availabillity():
    global availabilitydf
    availabilitydf = pd.read_csv(WDPATH+'/config'+'/chillers.config')#'config/chillers.config')/Users/nigarbutt/PycharmProjects/Chiller
    #return availabilitydf

def prepare_data():
    '''
    this function adds the RT capacity of chiller pairs
    :return: model in form of dataframe  read from data folder
    '''
    df1 = pd.read_excel(FILE_NAME, sheet_name=0)
    df1 = df1.fillna(0)

    for i in range(TOTAL_CHILLERS // 2):
        key_1 = 'RT CH-0' + str((2 * i) + 1) + ' AVG'
        if i != 4:
            key_2 = 'RT CH-0' + str((2 * i) + 2) + ' AVG'
            key_total = 'RT Sum (CH-0' + str((2 * i) + 1) + ',' + 'CH-0' + str((2 * i) + 2) + ')'
        else:
            key_2 = 'RT CH-' + str((2 * i) + 2) + ' AVG'
            key_total = 'RT Sum (CH-0' + str((2 * i) + 1) + ',' + 'CH-' + str((2 * i) + 2) + ')'

        df1[key_total] = df1.loc[(df1[key_1] > 0) & (df1[key_2] > 0), [key_1, key_2]].sum(axis=1)
        df1[key_total].fillna(0, inplace=True)
        #print(key_total)

        # required_df[(required_df[key_1] > 0) & (required_df[key_2] > 0)]

    return df1


df = prepare_data()  # pd.read_excel(FILE_NAME, sheet_name=0)


def calculate_temperature_bins(binrange=2):
    '''
    :param binrange: defines the size of temperature bin to decide the point of switching chiller rankings default 2
    :return:
    temperature_idx: list of  temperature bin touples [(0,2),(2,4),......] inclusive on left
    temperature_counts list of frequency of each temperature bin
    '''

    temperature_counts = []
    temperature_idx = []
    i = 0
    maxTemp = max(df[TEMPERATURE_KEY])
    while i < maxTemp:
        tbin = len(df[df[TEMPERATURE_KEY].between(i, i + binrange, inclusive='left')])
        key = (i, i + binrange)
        temperature_counts.append(tbin)
        temperature_idx.append(key)
        i = i + binrange

    return temperature_idx, temperature_counts


def remove_outliers(data, sigma=2):
    '''
    :param data: numeric list (float or integer) to remove outliers from
    :param sigma: coefficient to decide range of outliers based on sigma multiple of standard deviation
    :return: new_data after removing lower outliers
    '''
    mean = np.mean(data)
    std = np.std(data)
    new_data = data[data > (mean - (sigma * std))]
    return new_data

def celcius_to_fahreneit(celcius):
    '''
    :param celcius: temperature in celcius
    :return: temperature in fahrenhiet
    '''
    fahrenheit=(celcius*(9/5)) + 32
    return fahrenheit

def model_training(temperatureBin=2):
    '''
    create model for chiller pair and chiller ranking
    :param temperatureBin:
    :return: chillerpair_bins, chiller_bins, chiller_counts, expected_loads
    '''
    temperature_idx, temperature_counts = calculate_temperature_bins(temperatureBin)

    # chiller pair bins for temperature-efficiency

    chillerpair_bins = {}
    for temp_bin in temperature_idx:
        tdf = df[df[TEMPERATURE_KEY].between(temp_bin[0], temp_bin[1], 'left')]
        # print (i, len(tdf ))
        tbin = {}
        j = 1
        while j < 10:
            if j <= 8:
                key = 'KW/RT CH-0' + str(j) + ' AVG'
                key_p = 'KW/RT CH-0' + str(j + 1) + ' AVG'
                key2 = ('CH-0' + str(j), 'CH-0' + str(j + 1))
            else:
                key = 'KW/RT CH-0' + str(j) + ' AVG'

                key_p = 'KW/RT CH-' + str(j + 1) + ' AVG'
                key2 = ('CH-0' + str(j), 'CH-' + str(j + 1))

            j = j + 2

            ctdf1 = tdf[(tdf[key] > 0) & (tdf[key_p] > 0)][key]
            ctdf2 = tdf[(tdf[key] > 0) & (tdf[key_p] > 0)][key_p]
            lenctdf1 = len(ctdf1)
            lenctdf2 = len(ctdf2)
            if lenctdf1 > 0 and lenctdf2 > 0:
                std = (((np.std(ctdf1) ** 2) + (np.std(ctdf2) ** 2)) / 2) ** 0.5
                tbin[key2] = {MIN: (min(ctdf1) + min(ctdf2)) / 2,
                              MAX: (max(ctdf1) + max(ctdf2)) / 2,
                              AVG: (np.mean(ctdf1) + np.mean(ctdf2)) / 2,
                              'std': std,
                              'se': std / (lenctdf1 ** 0.5),  # standard error
                              FREQ: lenctdf1
                              }


            else:
                tbin[key2] = {MIN: 0,
                              MAX: 0,
                              AVG: 0,
                              'std': 0,
                              'se': 0,
                              FREQ: 0
                              }

        chillerpair_bins[temp_bin] = tbin

    # single chiller bins for temperature-efficiency

    chiller_bins = {}
    for temp_bin in temperature_idx:
        tdf = df[df[TEMPERATURE_KEY].between(temp_bin[0], temp_bin[1], 'left')]
        # print (i, len(tdf ))
        tbin = {}
        j = 1
        while j <= 10:
            if j <= 9:
                key = 'KW/RT CH-0' + str(j) + ' AVG'
                key2 = 'CH-0' + str(j)
            else:
                key = 'KW/RT CH-' + str(j) + ' AVG'

                key2 = 'CH-' + str(j)

            j = j + 1

            ctdf1 = tdf[tdf[key] > 0][key]
            lenctdf1 = len(ctdf1)
            if lenctdf1 > 0:
                std = np.std(ctdf1)
                tbin[key2] = {MIN: min(ctdf1),
                              MAX: max(ctdf1),
                              AVG: np.mean(ctdf1),
                              'std': std,
                              'se': std / (lenctdf1 ** 0.5),  # standard error
                              FREQ: lenctdf1
                              }


            else:
                tbin[key2] = {MIN: 0,
                              MAX: 0,
                              AVG: 0,
                              'std': 0,
                              'se': 0,
                              FREQ: 0
                              }

        chiller_bins[temp_bin] = tbin

    chiller_counts = {}
    for temp_bin in temperature_idx:
        tdf = df[df[TEMPERATURE_KEY].between(temp_bin[0], temp_bin[1], 'left')][RUNNING_CHILLER_COUNT]
        chiller_counts[temp_bin] = {MIN: min(tdf),
                                    MAX: max(tdf),
                                    AVG: np.mean(tdf),
                                    FULL: 10}

    expected_loads = {}  # temperaturebin->month->expected_load
    for temp_bin in temperature_idx:
        tdf = df[df[TEMPERATURE_KEY].between(temp_bin[0], temp_bin[1], 'left')]
        monthly_expected_capacity = {}
        for i in range(12):
            mtdf = tdf[tdf[MONTH] == i + 1][DCU_POWER]
            mtdf = remove_outliers(mtdf)
            if len(mtdf) <= 0:
                mtdf = tdf[DCU_POWER]
                mtdf = remove_outliers(mtdf, 1)

            monthly_expected_capacity[i + 1] = {MIN: np.ceil(min(mtdf)),
                                                MAX: np.ceil(max(mtdf)),
                                                AVG: np.ceil(np.mean(mtdf))}

        expected_loads[temp_bin] = monthly_expected_capacity

    return chillerpair_bins, chiller_bins, chiller_counts, expected_loads


#

BASIC_MODEL = model_training()


def update_basic_model(temperatureBin=2):
    global BASIC_MODEL
    BASIC_MODEL = model_training(temperatureBin)


def find_temperature_bin(temperature=20):
    for temp_bin in BASIC_MODEL[CHILLER_PAIR_IDX].keys():  # temperature bins
        # print(temp_bin)
        if temperature >= temp_bin[0] and temperature < temp_bin[1]:
            return temp_bin

    return None  # (20, 22)


def find_hourly_temperature_in_day(day=1, month=1, year=2018, hourbin=1):
    daydf = df[(df[DAY] == day) & (df[MONTH] == month)]
    hourly_temp = []
    hours = []
    #print(min(daydf[HOUR]), max(daydf[HOUR]), )

    #maxhr = max(daydf[HOUR])

    for hr in range(0,24, hourbin):#min(daydf[HOUR]), maxhr + 1, hourbin):
        #if hr == maxhr:
        #    temp = np.mean(df[(df[DAY] == day) & (df[MONTH] == month) & (df[HOUR].between(hr, hr + hourbin, 'left')) & (
        #                df[MINUTE] < 30)]['Wetbulb AVG'])
        #else:
        temp = np.mean(df[(df[DAY] == day) & (df[MONTH] == month) & (df[HOUR].between(hr, hr + hourbin, 'left'))][
                               'Wetbulb AVG'])

        if math.isnan(temp):
            temp = np.mean(df[(df[DAY] == day) & (df[MONTH] == month)]['Wetbulb AVG'] )
        hourly_temp.append(find_temperature_bin(temperature=temp))
        hours.append(hr )

        # print(hr, temp)
    #if hourbin == 1:
    #    temp = np.mean(
    #        df[(df[DAY] == day) & (df[MONTH] == month) & (df[HOUR].between(maxhr, maxhr + hourbin, 'left')) & (
    #                    df[MINUTE] > 30)][
    #            'Wetbulb AVG'])
   #     hourly_temp.append(find_temperature_bin(temperature=temp))
   #     hours.append(maxhr)

    # print(hourly_temp)

    return hours, hourly_temp


def estimate_expected_chillers_in_temperature_bin(hourly_temperature, expected_load=AVG):
    chiller_counts_temp = BASIC_MODEL[2]
    avgchillercount = []
    for tempbin in hourly_temperature:
        avgchillercount.append(math.ceil(chiller_counts_temp[(tempbin[0], tempbin[1])][expected_load]))

    return avgchillercount

# def get_all_available_chiller_pairs(tempbin):
#     chiller_pairs = BASIC_MODEL[CHILLER_PAIR_IDX]
#     kindex = chiller_pairs[tempbin].keys()
#     df2 = pd.DataFrame({AVG: pd.DataFrame.from_dict(chiller_pairs[tempbin]).iloc[2]}, index=kindex)
#
#     selected_pairs = []
#     ##print(df2)
#     for i in range(no_of_pairs):
#         pair = df2.index[i]
#         pair_availability = check_chiller_pair_availability(pair)
#         if pair_availability:
#             selected_pairs.append(pair)
#
#     return selected_pairs

def select_most_efficient_chiller_pair_for_tempbin(tempbin, count=10):
    chiller_pairs = BASIC_MODEL[CHILLER_PAIR_IDX]
    no_of_pairs = count // 2
    kindex = chiller_pairs[tempbin].keys()
    df2 = pd.DataFrame({AVG: pd.DataFrame.from_dict(chiller_pairs[tempbin]).iloc[2]}, index=kindex)

    df2 = df2.sort_values(AVG)

    selected_pairs = []
    ##print(df2)
    for i in range(no_of_pairs):
        pair = df2.index[i]
        pair_availability = check_chiller_pair_availability(pair)
        if pair_availability:
            selected_pairs.append(pair)

    return selected_pairs


def sorted_efficient_chiller_for_tempbin(tempbin, count=10):
    chillers = BASIC_MODEL[CHILLERS_IDX]
    no_of_chillers = count  # // 2
    kindex = chillers[tempbin].keys()
    df2 = pd.DataFrame({AVG: pd.DataFrame.from_dict(chillers[tempbin]).iloc[2]}, index=kindex)
    df2 = df2.sort_values(AVG)

    selected_chillers = []
    # print(df2)
    for i in range(no_of_chillers):
        chiller = df2.index[i]
        chiller_availability = check_chiller_availability(chiller)
        if chiller_availability:
            selected_chillers.append(df2.index[i])

    return selected_chillers


def select_next_efficient_single_chiller_for_tempbin(tempbin, modulespriority, hour):
    chiller_pairs = BASIC_MODEL[CHILLERS_IDX]
    kindex = list(chiller_pairs[tempbin].keys())
    df2 = pd.DataFrame({AVG: pd.DataFrame.from_dict(chiller_pairs[tempbin]).iloc[2]}, index=kindex)

    df2 = df2.sort_values(AVG)
    df2idx = list(df2.index)
    # i = 1
    for idx in df2idx:
        n = kindex.index(idx)
        #print(idx, kindex)
        #print (n)
        if len(modulespriority[int(n // 2)]) < hour+1:
            return n

    return 0


def getDemand_from_df(day, month, year, hour, temperatureRange, expected_load=AVG):
    key = DCU_POWER
    required_df = df[(df[DAY]==day) & (df[YEAR]== year) & (df[HOUR]==hour) &(
            df[MONTH] == month) &
                     (df[key] > 0)]
    if len(required_df) > 0:
        return required_df.iloc[0][key]
    else:
        return BASIC_MODEL[EXPECTED_LOAD_IDX][temperatureRange][month][expected_load]



def getDemand_completed_by_chiller_pair(temperatureRange, month, chillerpair):
    key = 'RT Sum (' + chillerpair[0] + ',' + chillerpair[1] + ')'
    required_df = df[(df[TEMPERATURE_KEY].between(temperatureRange[0], temperatureRange[1], inclusive='left')) & (
                df[MONTH] == month) &
                     (df[key] > 0)]
    if len(required_df) > 0:
        return np.ceil(np.mean(required_df[key]))
    else:
        required_df = df[(df[TEMPERATURE_KEY].between(temperatureRange[0], temperatureRange[1], inclusive='left')) & (
                df[key] > 0)]
        return np.ceil(np.mean(required_df[key]))

def getDemand_completed_by_chiller_single(temperatureRange, month, chiller):
    key = 'RT ' + chiller+ ' AVG'
    required_df = df[(df[TEMPERATURE_KEY].between(temperatureRange[0], temperatureRange[1], inclusive='left')) & (
                df[MONTH] == month) &
                     (df[key] > 0)]
    if len(required_df) > 0:
        return np.ceil(np.mean(required_df[key]))
    else:
        required_df = df[(df[TEMPERATURE_KEY].between(temperatureRange[0], temperatureRange[1], inclusive='left')) & (
                df[key] > 0)]
        return np.ceil(np.mean(required_df[key]))

def check_chiller_availability(chiller):
    '''chiller is string in formate str(Ch-01)'''
    return availabilitydf[chiller][0]

def check_chiller_pair_availability(pair):
    '''pair is tuple in formate (Ch-01,Ch-02)
    return true if both chillers in pair are available, else return false
    '''

    return availabilitydf[pair[0]][0] & availabilitydf[pair[1]][0]

def select_most_efficient_chillers_basedon_expectedload(hourly_temperature, charging, charging_capacity_rt, discharging_rt, day=1, month=1, year=2018,  expected_load = AVG, extra_rt=0):
    chiller_pairs = BASIC_MODEL[CHILLER_PAIR_IDX]
    expected_demands = BASIC_MODEL[EXPECTED_LOAD_IDX]
    pcindex = chiller_pairs[hourly_temperature[0]].keys()
    scidx = BASIC_MODEL[CHILLERS_IDX][hourly_temperature[0]].keys()
    modules = {}  # [[],[],[],[],[],[]]
    for i in range(5):
        modules[i] = []

    single_chillers = {}
    for i in range(10):
        single_chillers[i] = []
    #print(pcindex)
    pcindex = list(pcindex)  # list of chiller pairs
    scindex = list(scidx)
    #print(pcindex)

    RT_produced =  []
    chillers_running = []
    #print('&&&&&&&&&&&&&&&&&&&&&&&&')
    #print(charging_capacity_rt)
    #print('&&&&&&&&&&&&&&&&&&&&&&&&')
    #extra_rt = 0

    for i in range(len(hourly_temperature)):
        all_pairs = select_most_efficient_chiller_pair_for_tempbin(hourly_temperature[i], 10)
        if TEST:
            estimated_demand = getDemand_from_df(day, month, year, i, hourly_temperature[i], expected_load=AVG)#
        else:
            estimated_demand = expected_demands[hourly_temperature[i]][month][expected_load]
        demand_remaining = estimated_demand - discharging_rt[i] #demand to be filled by chillers is equal to total demand -demand filled by TES tank


        if charging[i]:
            demand_remaining = estimated_demand + charging_capacity_rt[i]
            print(i,"charging rt added")
        #print(demand_remaining)

        demand_remaining -= extra_rt
        complete_demand = demand_remaining

        #print(demand_remaining," after subtracting extra rt", extra_rt)
        extra_rt = 0
        priority = 1
        rt_sum  = 0
        chillers_count = 0
        chillers_used = []
        for pair in all_pairs:
            #print(pair)

            demand_filled = getDemand_completed_by_chiller_pair(hourly_temperature[i],month, pair)
            #print(demand_filled)
            demand_remaining = demand_remaining - demand_filled
            if demand_remaining >= 0:
                loc = pcindex.index(pair)
                modules[loc].append(priority)
                priority += 1
                rt_sum += demand_filled
                chillers_count += 2
                chillers_used.append(pair[0])
                chillers_used.append(pair[1])

            else:
                last_possible_pair = pcindex.index(pair)
                # things to do
                chiller_idx = select_next_efficient_single_chiller_for_tempbin(hourly_temperature[i], modules, i)
                if chiller_idx !=9:
                    chiller = 'CH-0'+str(chiller_idx+1)
                else:
                    chiller = 'CH-10'
                chiller_rt = getDemand_completed_by_chiller_single(hourly_temperature[i],month,chiller )
                if (demand_remaining + demand_filled) - chiller_rt <=0:
                    for k in range(10):
                        if k != chiller_idx:
                            single_chillers[k].append(0)
                        else:
                            single_chillers[k].append(priority)
                            chillers_used.append(chiller)
                    rt_sum += chiller_rt
                    chillers_count +=1
                else:
                    for k in range(10):
                       single_chillers[k].append(0)

                    modules[last_possible_pair].append(priority)
                    chillers_used.append(pair[0])
                    chillers_used.append(pair[1])

                    rt_sum += demand_filled
                    chillers_count +=2

                    #print(modules)



                #RT_produced.append(rt_sum)
                #chillers_running.append(chillers_count)

                break;

        for k in modules.keys():
            if len(modules[k]) < i + 1:
                modules[k].append(0)

        #print(modules)

        #print(chillers_used)

        for k in single_chillers.keys():
            if len(single_chillers[k]) < i + 1:
                single_chillers[k].append(0)

        #print(single_chillers)

        if demand_remaining > 0:
            remaining_free_chillers = sorted_efficient_chiller_for_tempbin(hourly_temperature[i], 10)
            for chiller in remaining_free_chillers:
                if chiller not in chillers_used:
                    demand_filled = getDemand_completed_by_chiller_single(hourly_temperature[i],month,chiller)
                    if demand_filled <= demand_remaining:
                        demand_remaining = demand_remaining - demand_filled
                        loc = scindex.index(chiller)
                        single_chillers[loc][i]=priority
                        priority += 1
                        rt_sum += demand_filled
                        chillers_count += 1
                        chillers_used.append(chiller)
                    else:
                        demand_remaining = demand_remaining - demand_filled
                        loc = scindex.index(chiller)
                        single_chillers[loc][i] = priority
                        priority += 1
                        rt_sum += demand_filled
                        chillers_count += 1
                        chillers_used.append(chiller)
                        break;

            if demand_remaining > 0:
                 print ('chillers unable to fill demand discharge from TES tank')

        #print(rt_sum,complete_demand, extra_rt)

        extra_rt = np.max(rt_sum - complete_demand,0)
        print("*",rt_sum, complete_demand, extra_rt)

        RT_produced.append(rt_sum)
        chillers_running.append(chillers_count)

            #discharge from tank and select operating condition based on demand required











    return modules, single_chillers, RT_produced, chillers_running, extra_rt
    # selected_pairs







def estimate_expected_load_of_bin(temperatureRange, month=1):
    expected_loads = BASIC_MODEL[EXPECTED_LOAD_IDX]
    #print('estimate_expected_load_of_bin', temperatureRange)
    #print(expected_loads)
    return expected_loads[temperatureRange][month]


def estimate_expected_load(hourly_temperatures,day=1, month=1, year= 2018, load=AVG):
    expected_loads = []
    if load == FULL:
        load = MAX

    #print(load, hourly_temperatures)
    i = 0

    for temp_bin in hourly_temperatures:
        if TEST:
            estimated_demand = getDemand_from_df(day, month, year, i, hourly_temperatures[i], expected_load=AVG)
        else:
            estimated_demand = estimate_expected_load_of_bin(temp_bin, month)[load]

        expected_loads.append(estimated_demand)
        i+=1

    return expected_loads


def kelvinToCelsius(kelvin):
    return kelvin - 273.15

def calculateWetbulbTemperature(temperature, rh):
    temperature_celsius = kelvinToCelsius(temperature)
    wetbulb= temperature_celsius * math.atan(0.151977 * math.sqrt(rh + 8.313659)) + math.atan(temperature_celsius + rh) - math.atan(rh - 1.676331) + 0.00391838 *math.pow(rh,(3/2)) * math.atan(0.023101 * rh) - 4.686035
    wetbulb = round(wetbulb,2)
    return wetbulb


def forecaste_hourly_temperature_in_day(hourBin=1):
    hours = []
    hourly_temperature = []
    # API key
    API_KEY = "d850f7f52bf19300a9eb4b0aa6b80f0d"  # "f949a40508bc4e25767250daef380f7f"
    # upadting the URL
    URL = "https://api.openweathermap.org/data/2.5/onecall?lat=25.2048&lon=55.2708" + "&appid=" + API_KEY
    # HTTP request
    print(URL)
    response = requests.get(URL)
    day = 1
    month = 1
    # checking the status code of the request
    if response.status_code == 200:
        # getting data in the json format
        data = response.json()
        # getting the main dict block
        print(data)
        main = data['hourly']
        limit = 24
        for hr in main:

            ts = int(hr['dt'])
            date = datetime.utcfromtimestamp(ts)
            hours.append(date.hour)
            temperature = calculateWetbulbTemperature(int(hr['temp']), (float(hr['humidity'])))
            temperaturebin = find_temperature_bin(temperature)
            hourly_temperature.append(temperaturebin)
            print(hr['dt'])
            # ts = int(hr['dt'])

            # if you encounter a "year is out of range" error the timestamp
            # may be in milliseconds, try `ts /= 1000` in that case
            print(date, hr['temp'],
                  temperature,
                  temperaturebin)

            if limit == 24:
                day = date.day
                month = date.month

            limit -= 1
            if limit == 0:
                break



    else:
        # showing the error message
        print("Error in the HTTP request " + str(response.status_code))

    return hours, hourly_temperature, day, month


def find_hours_demand_exceed_capacity_chiller(hours, hourly_temperatures, month, load=AVG):
    discharging = []
    discharging_rt = []
    discharging_flowrate = []
    charging_capacity = []
    for i in range(len(hours)):
        expected_demand = estimate_expected_load_of_bin(hourly_temperatures[i],month)[load]
        all_pairs = select_most_efficient_chiller_pair_for_tempbin(hourly_temperatures[i])
        capacity = 0
        selected_chillers = []
        for pair in all_pairs:
            capacity += getDemand_completed_by_chiller_pair(hourly_temperatures[i], month, pair)
            selected_chillers.append(pair[0])
            selected_chillers.append(pair[1])# = list(np.unique(all_pairs))

        all_chillers = sorted_efficient_chiller_for_tempbin(hourly_temperatures[i])
        for chiller in all_chillers:
            if chiller not in selected_chillers:
                capacity += getDemand_completed_by_chiller_single(hourly_temperatures[i], month,chiller)

        discharging.append(expected_demand>=capacity)
        if expected_demand-capacity > 0:
            discharging_rt.append(expected_demand-capacity)
            required_refrigeration_tonage =  (expected_demand-capacity) * 1.05
            flowrate = calculate_flowrate_given_refrigeration_tonage(required_refrigeration_tonage)
            discharging_flowrate.append(flowrate)
            charging_capacity.append(0)
        else:
            discharging_rt.append(0)
            discharging_flowrate.append(0)
            charging_capacity.append(capacity- expected_demand)



    return discharging, discharging_rt, discharging_flowrate, charging_capacity




def get_required_minimum_volume(discharging_rt):
    required_rt = np.ceil(np.sum(discharging_rt) * 1.05)
    inflow, outflow = get_TES_tank_temperatures()
    delta_t = inflow - outflow
    volume = ((required_rt * 24) / delta_t ) * 60
    return volume

def get_required_volume_for_rt_for_hour(required_tonage):
    inflow, outflow = get_TES_tank_temperatures()
    delta_t = inflow - outflow
    volume = ((required_tonage * 24) / delta_t) * 60
    return volume

def get_avg_sundown_sunup_temperatures(hours, hourly_temperature):
    sunuptemp = 0
    sundowntemp = 0
    sunupcount = 0
    sundowncount = 0
    for i in range(len(hours)):

        if hours[i]<sunrise_time | hours[i]>sunset_time:
            sundowncount += 1
            sundowntemp = sundowntemp + hourly_temperature[i][0] + hourly_temperature[i][1]

        elif hours[i]>=sunrise_time | hours[i]<=sunset_time:
            sunupcount += 1
            sunuptemp = sunuptemp + hourly_temperature[i][0] + hourly_temperature[i][1]
        else:
            raise Exception('Issue while calculating temperature averages')

    return sundowntemp/sundowncount, sunuptemp/sunuptemp

def volume_after_discharge_for_hour_at_flowrate(current_volume, flowrate=12000):
    old_time = current_volume/flowrate
    new_time = old_time - 60
    new_volume = np.ceil( new_time * flowrate)

    return new_volume

def get_flowrate_given_volume(remaining_volume, hourbin=1):
    flowrate = remaining_volume / (60*hourbin)
    if flowrate > 12000:
        raise Exception('flowrate exceeds harrdware limit')
    return flowrate

def find_flowrate_for_volume(charging_rt, volume, max_volume):
    prev_flowrate = calculate_flowrate_given_refrigeration_tonage(charging_rt)
    prev_volume = volume + (prev_flowrate * 60)
    new_charging_rt = charging_rt / 2
    hr_charging_flowrate = calculate_flowrate_given_refrigeration_tonage(new_charging_rt)
    new_volume = volume + (hr_charging_flowrate * 60)
    i = 0
    while(new_volume > max_volume and i < 10):
        prev_flowrate = hr_charging_flowrate
        prev_volume = new_volume
        new_charging_rt = charging_rt/2
        hr_charging_flowrate = calculate_flowrate_given_refrigeration_tonage(new_charging_rt)
        new_volume = volume + (hr_charging_flowrate * 60)
        i+=1

    prev_volume = np.ceil( prev_volume)
    prev_flowrate= np.ceil(prev_flowrate)
    return prev_flowrate, prev_volume


def higher_temperature_hours_remaining(hourly_temperature, current_index):
    if current_index+1>= len(hourly_temperature):
        return 0
    count = 0
    current_temp = hourly_temperature[current_index][0]
    for i in range(current_index+1,  len(hourly_temperature)):
        if hourly_temperature[i][0]>current_temp:
            count +=1

    return count

def isTemperature_higher_than_day_average(hourly_temperature, current_index):
    current_temp = np.mean(hourly_temperature[current_index])
    day_avg = np.mean(hourly_temperature)
    if current_temp>day_avg:
        return True
    else:
        return False




def TES_tank_calculation(hours, hourly_temperature, discharging, discharging_rt, discharging_flowrate, charging_capacity_rt, passed_volume=0):

    #sundowntemp, sunuptemp = get_avg_sundown_sunup_temperatures(hours, hourly_temperature)
    #print(len(hours),len(discharging),len(discharging_rt),len(discharging_flowrate),len(charging_capacity_rt))

    minimum_required_volume = get_required_minimum_volume(discharging_rt)
    if TEST and passed_volume>0:
        current_volume = passed_volume
    else:
        current_volume = calculate_current_volume_of_TES_tank()
    max_volume = calculate_current_volume_of_TES_tank(69)
    volume_to_charge = max_volume - current_volume

    charging_flowrates = []
    charging = []
    updated_discharging = []
    updated_discharging_flowrates = []
    updated_discharging_rt = []
    tank_volume = []

    print("volume of TES tank before day:", current_volume, minimum_required_volume)

    #if current_volume<max_volume:
    #    charging_required_flag = True;




    for i in range(len(hours)):

        #charging condition
        #print (hours[i])
        if charging_capacity_rt[i] > 5400:
            charging_capacity_rt[i] = 5400
        if discharging[i] == False and hours[i]<sunrise_time:#start time #| hours[i]>sunset_time: # sundown
            if current_volume < max_volume:
                hr_charging_flowrate = calculate_flowrate_given_refrigeration_tonage(charging_capacity_rt[i])
                new_volume = current_volume + (hr_charging_flowrate * 60)
                #charging_required_flag = False
                if new_volume < max_volume + 1000:

                    current_volume = new_volume #update volume
                else:
                    remaining_volume = max_volume - current_volume
                    hr_charging_flowrate = get_flowrate_given_volume(remaining_volume)
                    current_volume = current_volume + (hr_charging_flowrate * 60)
                    #hr_charging_flowrate,current_volume = find_flowrate_for_volume(charging_capacity_rt[i], current_volume, max_volume)

                hr_charging_flowrate = int(hr_charging_flowrate)
                charging.append(True)
                charging_flowrates.append(hr_charging_flowrate)

                updated_discharging.append(False)
                updated_discharging_flowrates.append(0)
                updated_discharging_rt.append(0)

            else:
                charging.append(False)
                charging_flowrates.append(0)
                updated_discharging.append(False)
                updated_discharging_flowrates.append(0)
                updated_discharging_rt.append(0)

        elif discharging[i] == False and hours[i]>sunset_time:
            if current_volume < max_volume:
                hr_charging_flowrate = calculate_flowrate_given_refrigeration_tonage(charging_capacity_rt[i])
                new_volume = current_volume + (hr_charging_flowrate * 60)
                # charging_required_flag = False
                if new_volume < max_volume + 1000:
                    #charging.append(True)
                    #charging_flowrates.append(hr_charging_flowrate)
                    current_volume = new_volume  # update volume
                else:
                    remaining_volume = max_volume - current_volume
                    hr_charging_flowrate = get_flowrate_given_volume(remaining_volume)
                    current_volume = current_volume + (hr_charging_flowrate * 60)
                    #hr_charging_flowrate, current_volume = find_flowrate_for_volume(charging_capacity_rt[i], current_volume, max_volume)

                hr_charging_flowrate = int(hr_charging_flowrate)
                charging.append(True)
                charging_flowrates.append(hr_charging_flowrate)


            else:
                charging.append(False)
                charging_flowrates.append(0)

            updated_discharging.append(False)
            updated_discharging_flowrates.append(0)
            updated_discharging_rt.append(0)
        # discharging conditions
        elif discharging[i] == False and (hours[i]>=sunrise_time or hours[i]<=sunset_time):
            #print('sun-up')
            if current_volume > minimum_required_volume:
                usable_volume = current_volume - minimum_required_volume
                rem_hours, rem_minutes = discharge_time_remaining_provided_refrigeration_tonage(current_volume=usable_volume)
                #print(hours[i],rem_hours, sunset_time - hours[i])
                if hours[i]>11 and rem_hours >= (sunset_time - hours[i]) and rem_hours > 2: #hours[i]>11 and #and rem_hours > 5: #noon time
                    rt = calculate_refrigeration_tonage_given_flowrate()
                    updated_discharging_rt.append(rt)
                    updated_discharging_flowrates.append(12000)
                    updated_discharging.append(True)
                    current_volume = np.ceil( volume_after_discharge_for_hour_at_flowrate(current_volume))
                else:
                    updated_discharging_flowrates.append(0)
                    updated_discharging.append(False)
                    updated_discharging_rt.append(0)


            else:
                updated_discharging_flowrates.append(0)
                updated_discharging.append(False)
                updated_discharging_rt.append(0)
            #################
            charging.append(False)
            charging_flowrates.append(0)
        #discharging condition
        elif discharging[i] == True:
            charging.append(False)
            charging_flowrates.append(0)
            if current_volume > minimum_required_volume:
                req_discarging_rt = discharging_rt[i]
                volume_needed = volume_after_discharge_for_hour_at_flowrate(minimum_required_volume, discharging_flowrate[i])
                extra_discharge_vol = volume_after_discharge_for_hour_at_flowrate(current_volume)
                rt = calculate_refrigeration_tonage_given_flowrate(12000)
                if extra_discharge_vol >  volume_needed:
                    updated_discharging_rt.append(rt)
                    updated_discharging_flowrates.append(12000)
                    updated_discharging.append(True)
                    current_volume = extra_discharge_vol#volume_after_discharge_for_hour_at_flowrate(current_volume)

                else:
                    current_volume = volume_after_discharge_for_hour_at_flowrate(current_volume, discharging_flowrate[i])
                    updated_discharging_rt.append(discharging_rt[i])
                    updated_discharging_flowrates.append(discharging_flowrate[i])
                    updated_discharging.append(True)

                minimum_required_volume = volume_needed

            else:
                raise Exception('TES tank unable to fullfill demand of plant')
        else:
            charging.append(False)
            charging_flowrates.append(0)
            updated_discharging_flowrates.append(0)
            updated_discharging.append(False)
            updated_discharging_rt.append(0)

        tank_volume.append(current_volume)


    print("volume of TES tank after day:",current_volume)


    return charging, charging_flowrates, charging_capacity_rt, updated_discharging, updated_discharging_flowrates, updated_discharging_rt, tank_volume




def create_graph(hours, day, month, year):
    gdf = pd.read_excel(WDPATH+'/data/KW_consumption.xlsx', sheet_name=0)#/Users/nigarbutt/PycharmProjects/Chiller
    if (year>2021 or year<2018):
        year = 2020
    tdf = gdf[gdf['date'] == datetime(year, month, day).strftime("%Y-%m-%d")]
    if len(tdf)<5:
        year = 2020
        tdf = gdf[gdf['date'] == datetime(year, month, day).strftime("%Y-%m-%d")]


    print (tdf)

    hrs = tdf['hour'].tolist()
    historical = tdf['historical'].tolist()
    estimated = tdf['recommended'].tolist()
    plt.plot(hrs, historical, label="historical")
    plt.plot(hrs, estimated, label="recommended")
    plt.title('Historical Vs Recommended KW consumption')
    plt.xlabel('time')
    plt.ylabel('KW')
    plt.legend()
    # plt.show()
    plt.savefig('fig.png')
    plt.cla()



def estimate_schedule(day=1, month=1, year=2018, expected_load=AVG, temperatureBin=1, hourBin=1, load_balancing=False,
                      TES_tank=False, forecaste=False, volume=0, extra_rt = 0):
    print(day, '-', month, '-', year)

    if not TEST or volume == 0:

        update_basic_model(temperatureBin)
        update_availabillity()
        print("updating model")

    chiller_pairs = BASIC_MODEL[CHILLER_PAIR_IDX]

    if not forecaste:
        hours, hourly_temperature = find_hourly_temperature_in_day(day, month, year, hourBin)
        create_graph(hours, day, month, year)
    else:
        hours, hourly_temperature , day, month= forecaste_hourly_temperature_in_day(hourBin)
        now = datetime.now()
        year = now.year#2022
        month = now.month#10
        day = now.day#20
        create_graph(hours, day, month, year)


    expected_demands = estimate_expected_load(hourly_temperature, day, month, year, expected_load)

    kindex = list(chiller_pairs[hourly_temperature[0]].keys())
    scidx = list(BASIC_MODEL[CHILLERS_IDX][hourly_temperature[0]].keys())

    chillercount = estimate_expected_chillers_in_temperature_bin(hourly_temperature, expected_load)

    discharging, discharging_rt, discharging_flowrate, charging_capacity_rt = find_hours_demand_exceed_capacity_chiller(
        hours, hourly_temperature, month)

    charging, charging_flowrates, charging_capacity_rt, discharging, discharging_flowrate, discharging_rt, tank_volume = \
        TES_tank_calculation(hours, hourly_temperature, discharging, discharging_rt, discharging_flowrate,
                             charging_capacity_rt,passed_volume=volume)

    modules, single_chillers,  RT_produced, chillers_running, extra_rt = \
        select_most_efficient_chillers_basedon_expectedload(hourly_temperature, charging, charging_capacity_rt, \
                                                            discharging_rt,day=day, month=month,year=year, expected_load=expected_load,extra_rt=extra_rt )
    #select_most_efficient_chiller_pairs(hourly_temperature, chillercount)

    #print(modules)
    #print(len(tank_volume),len(discharging),len(charging))

    #discharging, discharging_rt, discharging_flowrate, charging_capacity = find_hours_demand_exceed_capacity_chiller(hours, hourly_temperature, month)
    #x =
    dates = []
    for i in range(len(hours)):
        if forecaste and hours[i] == 0:
            day = day +1
        dates.append(datetime(year, month, day, hours[i]))



    result = pd.DataFrame({'date':dates,
                            'hour': hours,
                           'temperature': hourly_temperature,
                           'old chiller counts': chillercount,
                           'new chiller counts': chillers_running,
                           'expected demand': expected_demands,
                           'produced rt': RT_produced,
                           str(kindex[0]): modules[0],
                           str(kindex[1]): modules[1],
                           str(kindex[2]): modules[2],
                           str(kindex[3]): modules[3],
                           str(kindex[4]): modules[4],
                           str(scidx[0]): single_chillers[0],
                           str(scidx[1]): single_chillers[1],
                           str(scidx[2]): single_chillers[2],
                           str(scidx[3]): single_chillers[3],
                           str(scidx[4]): single_chillers[4],
                           str(scidx[5]): single_chillers[5],
                           str(scidx[6]): single_chillers[6],
                           str(scidx[7]): single_chillers[7],
                           str(scidx[8]): single_chillers[8],
                           str(scidx[9]): single_chillers[9],
                           'TES Discharging': discharging,
                           'Discharging Flowrate': discharging_flowrate,
                           'TES Charging': charging,
                           'Charging Flowrate': charging_flowrates,
                           'Tank Volume': tank_volume

                           })  # .from_dict(hourly_temperature).transpose()

    if TEST:
        return result, extra_rt
    return result



def get_level_of_TES_tank():

    tes_df = pd.read_csv(TES_SENSOR_FILEPATH,sep=',')
    level = 1
    keys = list(tes_df.keys())
    for i in range(2, len(keys)):
        if tes_df.iloc[0][keys[i]] > 4:
            level = i-2
            break
    return level;


def get_height_of_sensor(level=1):
    height = 316 # in mm
    sensor = 2 # first sensor is at height 316 so starting from sensor 2
    while sensor<=level and sensor<=70:
        if sensor%10 == 0:
            height += 616 # in mm
        elif sensor <= 9:
            height +=291
        else:
            height += 292

        sensor += 1

    height = height/1000 #height in meters

    return height

def calculate_current_volume_of_TES_tank(level_of_TES_tank = 0):
    # usable volume of water  = {Pi x (D_inside)^2 / 4 } x (HTX - Height of upper plate of bottom diffuser)
    PI = math.pi
    TES_diameter = 29.6 # in meters
    TES_radius = TES_diameter/2
    if level_of_TES_tank == 0:
        level_of_TES_tank = get_level_of_TES_tank()
    sensor_height = get_height_of_sensor(level_of_TES_tank) # in meters
    up_plate_low_diffuser_height = 0.588 #in meters



    usable_water_height = sensor_height - up_plate_low_diffuser_height

    usable_water_volume = PI * math.pow(TES_radius,2) * usable_water_height # in meter cube

    usable_water_volume = (usable_water_volume * 1000) /3.785412 # in usg-gallons

    usable_water_volume = int (usable_water_volume)

    return usable_water_volume


def get_TES_tank_temperatures():
    # get them from file in fahrenhiet
    tes_df = pd.read_csv(TES_SENSOR_FILEPATH, sep=',')
    warm = tes_df.iloc[0][TES_OUTLET_KEY]
    cold = tes_df.iloc[0][TES_INLET_KEY]
    warm = celcius_to_fahreneit(warm)
    cold = celcius_to_fahreneit(cold)

    return warm, cold  #48, 37.1#66#network_temperature, tank_chilled_temperature

def calculate_refrigeration_tonage_given_flowrate(flowrate = 12000): #hardware limit

    network_temperature, tank_chilled_temperature = get_TES_tank_temperatures()#in fahrenheit
    delta_temperature = network_temperature - tank_chilled_temperature
    required_refrigeration_tonage = (flowrate * delta_temperature)/24

    print(flowrate, delta_temperature, required_refrigeration_tonage)

    if required_refrigeration_tonage > 5400:

        print('TES RT exceeds hardware limits', required_refrigeration_tonage)
        required_refrigeration_tonage = 5400
        #raise Exception('flowrate exceeds hardware limits')

    return required_refrigeration_tonage


def calculate_flowrate_given_refrigeration_tonage(required_refrigeration_tonage = 4500): #hardware limit

    network_temperature, tank_chilled_temperature = get_TES_tank_temperatures()#in fahrenheit
    delta_temperature = network_temperature - tank_chilled_temperature
    flowrate = (required_refrigeration_tonage * 24 )/ delta_temperature

    #print(flowrate, delta_temperature)

    if flowrate > 12000:

        #rt = calculate_refrigeration_tonage_given_flowrate(flowrate)
        print('flowrate exceeds hardware limits', flowrate)
        flowrate = 12000
        #raise Exception('flowrate exceeds hardware limits')

    return flowrate


def discharge_time_remaining_provided_flow_rate(flowrate, current_volume=None):
    if current_volume is None:
        current_volume = calculate_current_volume_of_TES_tank()

    minutes = current_volume/flowrate
    hours = minutes // 24
    minutes =  minutes - hours*24
    minutes = math.floor(minutes)

    return hours, minutes; #in

def discharge_time_remaining_provided_refrigeration_tonage(required_refrigeration_tonage=4500, current_volume=None):
    flowrate = calculate_flowrate_given_refrigeration_tonage(required_refrigeration_tonage)
    dtime = discharge_time_remaining_provided_flow_rate(flowrate,current_volume)
    return dtime



if __name__ == "__main__":
    print(WDPATH)
    #day = 17
    #month = 7
    #year = 2022
    #hourBin = 1
    #create_graph(None,17,7,2020)

'''
    tdf, extra_rt = estimate_schedule()
    tdf.to_csv('out_reduced_rt.csv')
    current_volume = tdf.iloc[23]['Tank Volume']
    for year in range(2018,2022):
        for month in range(1,13):
            if month == 2:
                if year%4 ==  0:
                    days = 29
                else:
                    days = 28
            elif month in [1,3,5,7,8, 10, 12]:
                days = 31
            else:
                days = 30
            for day in range(1, days+1):
                tdf_1,extra_rt = estimate_schedule(day,month,year,volume=current_volume,extra_rt=extra_rt)
                current_volume = tdf_1.iloc[23]['Tank Volume']#[23]
                tdf = pd.concat([tdf, tdf_1], ignore_index=True, axis=0)

        tdf.to_csv('out_reduced_rt-'+str(year)+'.csv')


  update_availabillity()

    pt = calculate_flowrate_given_refrigeration_tonage(5400)
    print (pt)

    hours, hourly_temperature = find_hourly_temperature_in_day(day, month, year, hourBin)
    current_volume = calculate_current_volume_of_TES_tank()
    time_rem = discharge_time_remaining_provided_refrigeration_tonage()
    print(current_volume, time_rem, 5400)
    print(hours)
    discharging, discharging_rt, discharging_flowrate,charging_capacity_rt = find_hours_demand_exceed_capacity_chiller(hours,hourly_temperature,month)

    charging, charging_flowrates, charging_capacity_rt, updated_discharging, updated_discharging_flowrates, updated_discharging_rt, tank_volume = \
    TES_tank_calculation(hours, hourly_temperature, discharging, discharging_rt, discharging_flowrate, charging_capacity_rt)
    for i in range (len(hours)):
        print(hours[i], hourly_temperature[i],discharging[i], charging[i], charging_flowrates[i], charging_capacity_rt[i], updated_discharging[i], updated_discharging_flowrates[i], updated_discharging_rt[i], tank_volume[i])#discharging[i], discharging_rt[i], charging_capacity_rt[i])


    print(availabilitydf)
    print(np.unique(hourly_temperature,axis=0))
    flag = check_chiller_pair_availability(('CH-01','CH-02'))
    if flag:
        print('chiller pair available')
    else:
        print ('unavailable')

    flag2 = check_chiller_availability('CH-01')
    if flag2:
        print('chiller 1 available')
    else:
        print('chiller 1 unavailable')

    flag3 = check_chiller_availability('CH-02')
    if flag3:
        print('chiller 2 available')
    else:
        print('chiller 2 unavailable')
    select_most_efficient_chillers_basedon_expectedload(hourly_temperature,month)

    # prioritise charging 0
    # if temperature increases later increase priority of charging

    # temperature_idx, temperature_counts = calculate_temperature_bins()
    #print(df['RT Sum (CH-05,CH-06)'])
    #print(getDemand_completed_by_chiller_pair((20,22),4,('CH-05','CH-06')))

    #print(forecaste_hourly_temperature_in_day())
    #print(np.min(df[DCU_POWER]),np.max(df[DCU_POWER]))

    #print(np.min(df[RT_SUM]),np.max(df[RT_SUM]))

    #print(calculate_current_volume_of_TES_tank(), discharge_time_remaining_provided_flow_rate(12000))


#5568
#5912
#5738 -> 8
'''