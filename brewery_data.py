#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import requests
import time

while True:
    r = requests.get("https://api.openbrewerydb.org/v1/breweries")
    if r.status_code==200:
        data = r.json()
        print(data)
        time.sleep(60)
        
    else:
        exit()


# In[2]:


get_ipython().system('pip install pymongo[srv]')


# In[1]:


import requests
import time
from pymongo import MongoClient


client = MongoClient("mongodb+srv://margegbe:k6ewklnVWbhGuNIE@cluster123.jmfakxo.mongodb.net/breweryData?retryWrites=true&w=majority")
db = client.get_database('breweryData')
records = db.Brewery

while True:
    try:
        # Attempt to fetch data from the Open Brewery DB API
        r = requests.get("https://api.openbrewerydb.org/breweries")
        if r.status_code == 200:
            data = r.json()
            # Insert data into MongoDB collection
            if data:
                insert_result = records.insert_many(data)
                print(f"Inserted {len(insert_result.inserted_ids)} records.")
            else:
                print("No data fetched from API.")
        else:
            print(f"Failed to fetch data: Status code {r.status_code}")
            break  
        
        # Sleep for 60 seconds before the next fetch
        time.sleep(60)
        
    except requests.exceptions.RequestException as e:
        print(f"Request exception occurred: {e}")
        break  
        
    except Exception as e:
        print(f"An error occurred: {e}")
        break 


# In[3]:


import requests
import time
from pymongo import MongoClient

client = MongoClient("mongodb+srv://margegbe:k6ewklnVWbhGuNIE@cluster123.jmfakxo.mongodb.net/breweryData?retryWrites=true&w=majority")
db = client.get_database('breweryData')
records = db.Brewery

list(records.find({}))


# In[4]:


# Fetching all documents in the Brewery collection, including only the "name" field and excluding the "_id" field
all_documents = records.find({}, {"name": 1, "_id": 0})

# Iterating through the documents and printing the "name" field
for document in all_documents:
    print(document)


# In[5]:


get_ipython().system('pip install dash')
get_ipython().system('pip install pandas')


# In[8]:


import dash                                                    
from dash import html, dcc, Input, Output, State, dash_table
import pandas as pd                                             
import plotly.express as px
import pymongo   
from pymongo import MongoClient
from bson.objectid import ObjectId

# Connect to server on the cloud
client = MongoClient("mongodb+srv://margegbe:k6ewklnVWbhGuNIE@cluster123.jmfakxo.mongodb.net/breweryData?retryWrites=true&w=majority")

db = client.get_database('breweryData')
records = db.Brewery

print(db)

# Go into the database I created
db = client["breweryData"]
# Go into one of my database's collection (table)
collection = db["Brewery"]

# Define Layout of App
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash('brewery_data', external_stylesheets=external_stylesheets,
                suppress_callback_exceptions=True)
server = app.server

app.layout = html.Div([
    html.H1('Web Application connected to a Live Database', style={'textAlign': 'center'}),
    
    # Input element
    dcc.Input(id='input-element', type='text', placeholder='Enter a value...'),
    
    # interval activated once/week or when page refreshed
    dcc.Interval(id='interval_db', interval=86400000 * 7, n_intervals=0),
    html.Div(id='mongo-datatable', children=[]),

    html.Div([
        html.Div(id='pie-graph', className='five columns'),
        html.Div(id='hist-graph', className='six columns'),
    ], className='row'),
    dcc.Store(id='changed-cell')
])

# Display Datatable with data from Mongo database
@app.callback(Output('mongo-datatable', component_property='children'),
              Input('interval_db', component_property='n_intervals'))
def populate_datatable(n_intervals):
    global collection  # Declare collection as a global variable
    # Convert the Collection (table) date to a pandas DataFrame
    df = pd.DataFrame(list(collection.find()))
    # Convert id from ObjectId to string so it can be read by DataTable
    df['_id'] = df['_id'].astype(str)
    print(df.head(20))

    return [
        dash_table.DataTable(
            id='our-table',
            data=df.to_dict('records'),
            columns=[{'id': p, 'name': p, 'editable': False} if p == '_id'
                     else {'id': p, 'name': p, 'editable': True}
                     for p in df],
        ),
    ]

# store the row id and column id of the cell that was updated
app.clientside_callback(
    """
    function (input,oldinput) {
        if (oldinput != null) {
            if(JSON.stringify(input) != JSON.stringify(oldinput)) {
                for (i in Object.keys(input)) {
                    newArray = Object.values(input[i])
                    oldArray = Object.values(oldinput[i])
                    if (JSON.stringify(newArray) != JSON.stringify(oldArray)) {
                        entNew = Object.entries(input[i])
                        entOld = Object.entries(oldinput[i])
                        for (const j in entNew) {
                            if (entNew[j][1] != entOld[j][1]) {
                                changeRef = [i, entNew[j][0]] 
                                break        
                            }
                        }
                    }
                }
            }
            return changeRef
        }
    }    
    """,
    Output('changed-cell', 'data'),
    Input('our-table', 'data'),
    State('our-table', 'data_previous')
)

# Update MongoDB and create the graphs
@app.callback(
    Output("pie-graph", "children"),
    Output("hist-graph", "children"),
    Input("changed-cell", "data"),
    Input("our-table", "data"),
)
def update_d(cc, tabledata):
    if cc is None:
        # Build the Plots
        pie_fig = px.pie(tabledata, values='brewery_type', names='_id')
        hist_fig = px.histogram(tabledata, x='state', y='_id')
    else:
        print(f'changed cell: {cc}')
        print(f'Current DataTable: {tabledata}')
        x = int(cc[0])

        # update the external MongoDB
        row_id = tabledata[x]['_id']
        col_id = cc[1]
        new_cell_data = tabledata[x][col_id]
        collection.update_one({'_id': ObjectId(row_id)},
                              {"$set": {col_id: new_cell_data}})
        # Operations guide - https://docs.mongodb.com/manual/crud/#update-operations

        pie_fig = px.pie(tabledata, values='brewery_type', names='_id')
        hist_fig = px.histogram(tabledata, x='state', y='_id')

    return dcc.Graph(figure=pie_fig), dcc.Graph(figure=hist_fig)

#if __name__ == '__main__':
     #app.run_server(debug=False, port=8051)


# In[ ]:




