# distributed_systems_project
Project for HY course distributed systems

## Installing dependencies and starting the application
You can install the dependencies required by the project with poetry:
```
poetry install
```

After you have installed the dependencies, you can start the server with the following command:

```
poetry run invoke start-server --id <server_id> (1, 2 or 3)
```

A server with the lowest ID is the LEADER.
Сonsider changing SERVERS_LIST for clients and PEERS_CONFIG for servers if ports are occupied.

Likewise the client can be started with the following command:

```
poetry run invoke start-client
```
