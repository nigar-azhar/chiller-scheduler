import streamlit as st
from datetime import date, datetime
import pandas as pd
from streamlit.proto.SessionState_pb2 import SessionState

import chiller_efficiency as ce
ce.TEST  = False
#global df


if 'df' not in st.session_state:
    st.session_state['df'] = None
else:
    df = st.session_state['df']


if 'forecaste' not in st.session_state:
    st.session_state['forecaste'] = False
else:
    forecaste = st.session_state['forecaste']
st.set_page_config(page_icon="/Users/nigarbutt/PycharmProjects/Chiller/images/QuestIcon.png", page_title="QScheduler", layout='wide')
#st.set_page_config(layout="wide")
st.title("QScheduler")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    input_date = st.date_input(
        "Select Input date",
        date(2018, 1, 1),
        min_value=datetime.strptime("2018-01-01", "%Y-%m-%d"),

    )
    #if st.session_state['forecaste']:
        #input_date.date_input
    #df = None
#with

with col2:
    expected_load_sb = st.selectbox(
        "Expected Load", ("AVERAGE", "MAXIMUM","MINIMUM")
    )
with col3:
    temp_bin_box = st.number_input(
        "Temperature Bin",
        min_value=1,
        max_value=5
    )

with col4:
    forecast_checkbox = st.checkbox(
        "Temperature Forecasting",
        value=False
    )



def predictSchedule():
    #self.df = None
    date = input_date
    #date = date.toPyDate()
    if expected_load_sb == 'AVERAGE':
        expected_load = 'avg'
    elif expected_load_sb == 'MAXIMUM':
        expected_load = 'max'
    elif expected_load_sb == 'MINIMUM':
        expected_load = 'min'
    else:
        expected_load = 'avg'


    #expected_load = self.LOADS[self.expectedLoadCB.currentIndex()]
    tbin = temp_bin_box#temperatureBinSB.value()
    #hbin = self.hourBinSB.value()
    #df
    listOfGlobals = globals()

    listOfGlobals['df'] = ce.estimate_schedule(date.day, date.month, date.year, expected_load=expected_load,
                                   temperatureBin=tbin, forecaste=forecast_checkbox)

    dataview.dataframe(listOfGlobals['df'])
    st.session_state['df'] = listOfGlobals['df']

    #selection = aggrid_interactive_table(df=df)

    #model = dftv.pandasModel(self.df)
    #self.schedule.setModel(model)
    #self.update_graph()
    #self.graph.setPixmap(self.chillerpairs_pixmap)

    print(expected_load, tbin)
    #selection.update()

def saveSchedule():
    if st.session_state['df'] is not None:
        date = input_date
        date = str(date.day) + '-' + str(date.month) + '-' + str(date.year)

        filename = str('Schedule_' + date)
        st.session_state['df'].to_excel(filename + '.xlsx', index=False)
    else:
        st.write('generate a schedule first')


with col5:
    predict = st.button("Predict Schedule", on_click=predictSchedule)
    if st.session_state['df'] is not None:
        csv = st.session_state['df'].to_csv(index=False).encode('utf-8')
    else:
        csv = 'file not generated yet'

    save = st.download_button("Press to Download Schedule", csv,  "schedule.csv", "text/csv",   key='download-csv')
    #("Save Schedule",st.session_state['df'])#.button("Save Schedule", on_click=saveSchedule)

dataview = st.dataframe(st.session_state['df'])
st.image("fig.png")





#def main():

    # Note that page title/favicon are set in the __main__ clause below,
    # so they can also be set through the mega multipage app (see ../pandas_app.py).





    #predictSchedule(input_date,expected_load_sb, temp_bin_box,forecast_checkbox )

    #iris = pd.read_excel("/Users/nigarbutt/PycharmProjects/Chiller/data/power_consumption.xlsx", sheet_name=0)







#main()
