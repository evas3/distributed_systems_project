from invoke import task

@task
def start_client(ctx):
    ctx.run("python3 src/client/main.py")

@task(help={'id': "The unique ID of the server (1, 2, or 3)"})
def start_server(ctx, id=1):
    ctx.run(f"python3 src/server/main.py {id}")