# car-workshop-app

## Supabase Deployment

Set the following environment variables to store data in a Supabase
PostgreSQL database instead of the local SQLite file:

- `SUPABASE_URL`
- `SUPABASE_KEY`

The database must contain `cars` and `history` tables matching the schema
used by the application.