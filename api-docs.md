# Documentation for API Endpoints
All URIs are relative to https://beta.appflowy.cloud


| Class                  | Method                   | HTTP request                                                         | Description                                                                            |
|------------------------|--------------------------|----------------------------------------------------------------------|----------------------------------------------------------------------------------------|
| DatabaseFieldsApi      | getDatabaseFields        | GET /api/workspace/{workspace_id}/database/{database_id}/fields      | Retrieves a list of database fields in a selected database.                            |
| DatabaseRowDetailsApi  | getDatabaseRowDetails    | GET /api/workspace/{workspace_id}/database/{database_id}/row/detail  | Retrieves a list of database row details in a selected database.                       |
| DatabaseRowsApi        | createDatabaseRow        | POST /api/workspace/{workspace_id}/database/{database_id}/row        | Creates a new row in a selected database.                                              |
| DatabaseRowsApi        | getDatabaseRowIds        | GET /api/workspace/{workspace_id}/database/{database_id}/row         | Retrieves a list of database row ids in a selected database.                           |
| DatabaseRowsApi        | upsertDatabaseRow        | PUT /api/workspace/{workspace_id}/database/{database_id}/row         | Updates or creates a row in a selected database. (Upsert)                              |
| DatabaseRowsUpdatedApi | getDatabaseRowIdsUpdated | GET /api/workspace/{workspace_id}/database/{database_id}/row/updated | Retrieves a list of database row id which are recently updated in a selected database. |
| DatabasesApi           | getDatabases             | GET /api/workspace/{workspace_id}/database                           | Retrieves a list of database in a workspace                                            |
| OAuthApi               | gotrueToken              | POST /gotrue/token                                                   | Get a new access token and refresh token based on grant type                           |
| OAuthApi               | oauthRedirectToken       | GET /web-api/oauth-redirect/token                                    | Sign in with AppFlowy OAuth 2.0                                                        |
| WorkspacesApi          | getWorkspaceFolder       | GET /api/workspace/{workspace_id}/folder                             | Retrieves workspace folder or subfolder                                                |
| WorkspacesApi          | getWorkspaces            | GET /api/workspace                                                   | Retrieves a list of all workspaces                                                     |
