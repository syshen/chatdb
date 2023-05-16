import os
import json
import streamlit as st
import openai
import pandas as pd
from dotenv import load_dotenv
from tabulate import tabulate
from sqlalchemy import create_engine, text, MetaData
import plotly.express as px

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
    

def connectDB(db_type, host=None, port=None, user=None, password=None, database=None):
  try:
    if db_type == 'MySQL':
      driver = 'mysql+pymysql'
    elif db_type == 'PostgreSQL':
      driver = 'postgresql'
    engine = create_engine(f"{driver}://{user}:{password}@{host}:{port}/{database}")
    
    metadata = MetaData()
    metadata.reflect(bind=engine)
    dbInfo = ''
    for tb_name in metadata.tables:
      table = metadata.tables[tb_name]
      col_names = []
      col_types = []
      col_nullables = []
      for col in table.columns: 
        col_names.append(col.key)
        col_types.append(col.type)
        col_nullables.append(col.nullable)
      df = pd.DataFrame({
        'column_name': col_names,
        'type': col_types,
        'nullable': col_nullables
      })
      fmt = tabulate(df, headers='keys', tablefmt='psql')
      dbInfo += f"Table: {tb_name}\n"
      dbInfo += 'Schema:\n'
      dbInfo += fmt + "\n\n"

    return engine.connect(), dbInfo
  except:
    st.error(f"Failed to connect to the database on server {host} at port {port}. Please check your network connection and try again.")




def loadData(db_conn, db_type, query):
  if db_conn is None:
    raise Exception("Not connect to any database.")
  return pd.read_sql(query, con=db_conn)




def main():
  db_conn = None

  st.set_page_config(page_title="ChatDB")

  with st.sidebar:
    st.header("ChatDB")
    st.subheader("Configuration")
    openai.api_key = st.text_input("OpenAI API Key", 
                                  value=os.getenv("OPENAI_API_KEY") if os.getenv("OPENAI_API_KEY") else '',
                                  type="password")

    st.subheader("Database")

    db_options = ["MySQL", "PostgreSQL"]
    db_option_index = 0
    if os.getenv("DB_TYPE"):
      try:
        db_option_index = db_options.index(os.getenv("DB_TYPE"))
      except:
        db_option_index = 0

    db_selection = st.selectbox("Database", db_options, index=db_option_index)

    db_host = st.text_input("Hostname",
                            value=os.getenv("DB_HOST") if os.getenv("DB_HOST") else '')
    db_port = st.text_input("Port",
                            value=os.getenv("DB_PORT") if os.getenv("DB_PORT") else 0)
    db_user = st.text_input("Username",
                            value=os.getenv("DB_USER") if os.getenv("DB_USER") else '')
    db_pass = st.text_input("Password",
                            value=os.getenv("DB_PASS") if os.getenv('DB_PASS') else '',
                            type="password")
    db_database = st.text_input("Database",
                                value=os.getenv("DB_DATABASE") if os.getenv("DB_DATABASE") else '')


  if (db_host != '' and db_port != 0 and db_user != '' and db_pass != '' and db_database != ''):
    with st.spinner("Loading ..."):
      db_conn, db_info = connectDB(db_selection,
                                  host=db_host,
                                  port=db_port,
                                  user=db_user,
                                  password=db_pass,
                                  database=db_database)
  else:
    st.info("Set up your database info before you start using it.")
  
  if db_conn:
    input = st.text_area("Your question", placeholder="Put your question here", label_visibility="collapsed")
    if input:
      with st.spinner("AI is thinking ... "):
        response = chatCompletion(db_info, input)

      if response and response["choices"] and len(response["choices"]) > 0:
        content = json.loads(response["choices"][0]["message"]["content"])

        if 'response' in content:
          st.write(content['response'])
          return
        
        if 'error' in content:
          st.error(content['error'])
          return

        if 'SQL_codes' in content:
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
        else:
          st.write("Cannot recognize the response:")
          st.json(content)
      else:
        st.error("No valid response")

main()