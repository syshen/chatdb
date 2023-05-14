import os
import json
import streamlit as st
import openai
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import plotly.express as px

from google.cloud import bigquery
from google.oauth2 import service_account

load_dotenv()

def chatCompletion(db_info, question):
    prompt = f"""
You are a data analyst.
Use the info below about the database, like its name, list of tables, and table schemas, to answer user's questions:

{db_info}

----
To answer the user's question, you should provide an SQL code that can be used to query the database and retrieve the data.
You should also figure out if the results can be shown as a diagram. If they can, recommend a type of diagram to the user.
Your response should be in JSON format with key names like database, SQL_codes, columns, diagram_available, and diagram_type.
Available diagram type options: line, bar, hist, box, area, pie and scatter.

If the generated SQL code is going to change the data, just ignore the request and send back an error message.
    """

    return openai.ChatCompletion.create(
      model="gpt-4",
      messages=[
            { "role": "system", "content": prompt },
            { "role": "user", "content": f"``` {question} ````"}
      ],
      temperature=0.0,
      max_tokens=2000,
      top_p=0.1,
      frequency_penalty=0,
      presence_penalty=0
    )
    

def connectDB(db_type, host=None, port=None, user=None, password=None, gcp_credentials=None, gcp_project_id=None):
  if db_type == "BigQuery":
    credentials = service_account.Credentials.from_service_account_info(json.loads(gcp_credentials))
    return bigquery.Client(project=gcp_project_id, credentials=credentials)
  else:
    try:
      engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}:{port}")
      return engine.connect()
    except:
      st.error(f"Failed to connect to the database mydb on server {host} at port {port}. Please check your network connection and try again.")




def _collectBigQueryTableInfo(db_conn, dataset, tables):
  dbInfo = ''
  for table in tables:
    tbInfo = f"Table: {table}\nSchema:\n"
    table_schema = db_conn.get_table(f"{dataset}.{table}").schema
    for field in table_schema:
      tbInfo += f" - {field.name} ({field.field_type})\n"
    tbInfo += '\n'
    dbInfo += tbInfo
  print(dbInfo)
  return dbInfo


def collectDBInfo(db_conn, db_type='MySQL', bigquery_dataset=None, bigquery_tables=None):
  if db_type == 'BigQuery':
    return _collectBigQueryTableInfo(db_conn, bigquery_dataset, bigquery_tables)
  else:
    mysql_system_databases = ["information_schema", "mysql", "sys", "performance_schema"]
    if db_conn is None:
      raise Exception("Not connect to any database.")
  
    db_list = []
    result = db_conn.execute(text("SHOW databases;")).fetchall()
    for row in result:
      if row[0] not in mysql_system_databases:
        db_list.append(row[0])

    db_info = ""
    for db in db_list:
      db_conn.execute(text(f"USE {db};"))
      result = db_conn.execute(text("SHOW tables")).fetchall()
      db_info += f"Database: {db}\n\n"
      for row in result:
        table = row[0]

        columns = db_conn.execute(text(f"SHOW CREATE TABLE {table}")).fetchall()
        schema = columns[0][1]
        db_info += f"Table: {table}\n"
        db_info += f"Schema: {schema}\n\n"  

      db_info += "--------------\n"

    return db_info




def loadData(db_conn, db_type, query):
  if db_conn is None:
    raise Exception("Not connect to any database.")

  if db_type == 'BigQuery':
    results = db_conn.query(query)
    print(results)
  else:
    return pd.read_sql(query, con=db_conn)




def main():
  db_conn = None

  st.set_page_config(page_title="ChatDB")

  with st.sidebar:
    st.header("ChatDB")
    st.subheader("Configuration")
    openai.api_key = st.text_input("OpenAI API Key", value=os.getenv("OPENAI_API_KEY"), type="password")

    st.subheader("Database")
    db_options = ["MySQL", "PostgreSQL", "BigQuery"]
    db_option_index = 0
    if os.getenv("DB_TYPE"):
      try:
        db_option_index = db_options.index(os.getenv("DB_TYPE"))
      except:
        db_option_index = 0

    db_host = db_port = db_user = db_pass = None
    db_selection = st.selectbox("Database", db_options, index=db_option_index)
    if db_selection == "MySQL" or db_selection == "PostgreSQL":
      db_host = st.text_input("Hostname", value=os.getenv("DB_HOST"))
      db_port = st.text_input("Port", value=os.getenv("DB_PORT"))
      db_user = st.text_input("Username", value=os.getenv("DB_USER"))
      db_pass = st.text_input("Password", value=os.getenv("DB_PASS"), type="password")
    elif db_selection == "BigQuery":
      key_path = os.getenv('GCP_KEY_PATH')
      if key_path:
        with open(key_path, 'r') as f:
          key_file_content = f.read()

      gcp_key = st.text_area("Service Account JSON Key File", value=key_file_content)      
      bigquery_project = st.text_input("Project ID", value=os.getenv("BIGQUERY_PROJECT"))
      bigquery_dataset = st.text_input("Dataset", value=os.getenv("BIGQUERY_DATASET"))
      bigquery_tables = st.multiselect("Tables", os.getenv("BIGQUERY_TABLES").split(","))


  if db_selection == "MySQL" and db_host and db_port and db_user and db_pass:
    with st.spinner("Loading ..."):
      db_conn = connectDB(db_selection, host=db_host, port=db_port, user=db_user, password=db_pass)
      db_info = collectDBInfo(db_conn, db_type=db_selection)
  elif db_selection == "BigQuery" and gcp_key and bigquery_project and bigquery_dataset and bigquery_tables:
    with st.spinner("Loading ..."):
      db_conn = connectDB(db_selection, gcp_credentials=gcp_key, gcp_project_id=bigquery_project)
      db_info = collectDBInfo(db_conn, db_type=db_selection, bigquery_dataset=bigquery_dataset, bigquery_tables=bigquery_tables)
    
  input = st.text_area("Your question", placeholder="Put your question here", label_visibility="collapsed")
  if input:
    if not db_conn:
      st.error("Database isn't connected")
    else:
      with st.spinner("AI is thinking ... "):
        response = chatCompletion(db_info, input)

      if response and response["choices"] and len(response["choices"]) > 0:
        content = json.loads(response["choices"][0]["message"]["content"])

        if 'error' in content:
          st.error(content['error'])
          return

        if isinstance(content["SQL_codes"], list):
          sql = " ".join(content["SQL_codes"])
        else:
          sql = content["SQL_codes"]

        with st.spinner("Loading data ..."):
          data = loadData(db_conn, db_selection, sql)

          if content["diagram_available"] == "yes" or content["diagram_available"] is True:
            if content["diagram_type"] == "line":
              st.line_chart(data, x=data.columns[0], y=data.columns[1])
            elif content["diagram_type"] == "bar":
              st.bar_chart(data, x=data.columns[0], y=data.columns[1])
            elif content["diagram_type"] == "pie":
              fig = px.pie(data, values=data.columns[1], names=data.columns[0])
              st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("Open to see raw data"):
              st.dataframe(data)

            with st.expander("Open to see GPT response"):
              st.json(content)
          else:
            st.metric(data.columns[0], value=f"{data.values.flatten()[0]:,}")

            with st.expander("Open to see raw data"):
              st.dataframe(data)

            with st.expander("Open to see GPT response"):
              st.json(content)

          # st.table(data)
      else:
        st.error("No valid response")

main()