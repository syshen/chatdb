# ChatDB

## Introduction

ChatDB is a Streamlit demo application that translates human language into SQL queries and retrieves data from a database to present in diagram charts.

Demo

<video src="https://github.com/syshen/chatdb/assets/678081/415ca3d7-bd26-4446-9178-bf747a7b6100" controls="controls" style="max-width: 730px;">
</video>

Or check out the app [here](https://syshen-chatdb-chatdb-cwio9h.streamlit.app/).

## Setup

To install ChatDB, you will need the following:

* Python 3.6 or later
* Pip

Once you have installed these dependencies, you can clone the repository and install the project dependencies:

```
git clone https://github.com/[your-username]/chatdb.git
cd chatdb
pip3 install -r requirements.txt
```

## Usage

To start ChatDB, run the following command:

```
streamlit run chatdb.py
```

ChatDB will be available at http://localhost:8501.

To begin using ChatDB, you will need to configure your OpenAI API Key and database configuration. You can do this in either the UI or by creating a .env file with the following environmental variables:

* OPENAI_API_KEY
* DB_TYPE
* DB_HOST
* DB_PORT
* DB_USER
* DB_PASS

If you choose to configure your settings in the UI, you can do so by clicking on the "Settings" button. In the Settings dialog, you will need to enter your OpenAI API Key and your database configuration.

If you choose to configure your settings in a .env file, you will need to create a file called .env in the root directory of the ChatDB project. In the .env file, you will need to add the following lines:

```
OPENAI_API_KEY=

DB_TYPE=
DB_HOST=
DB_PORT=
DB_USER=
DB_PASS=
```

It supports "MySQL" and "PostgreSQL" as the DB_TYPE.

You can type in a natural language query in the text box and ChatDB will translate it into an SQL query and execute it against the database. The results of the query will be displayed in a diagram chart.

Here are some examples of natural language queries that you can use with ChatDB:

* What is the average salary of a software engineer in the United States?
* What are the top 10 most popular websites in the world?
* What is the weather like in London today?

ChatDB is still under development, but it can be a powerful tool for exploring and analyzing data. I hope you enjoy using it!
