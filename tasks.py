from invoke import task

@task
def start_client(ctx):
    ctx.run("python3 src/client/main.py")

@task
def start_server(ctx):
    ctx.run("python3 src/server/main.py")
