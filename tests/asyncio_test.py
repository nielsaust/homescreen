import asyncio

# Define your async function
async def main_task():
    try:
        while True:
            print("Running task...")
            await asyncio.sleep(2)  # Simulating ongoing work
    except asyncio.CancelledError:
        print("Task was cancelled")
    finally:
        print("Cleanup completed")

# This function runs the task and allows for restarting
async def run_task():
    while True:
        task = asyncio.create_task(main_task())  # Create a new task
        try:
            await task  # Await the task so we know when it's done
        except asyncio.CancelledError:
            print("Main loop received cancel signal, restarting task...")
        await asyncio.sleep(1)  # Optional delay before restarting

# Start the asyncio loop
try:
    asyncio.run(run_task())
except KeyboardInterrupt:
    print("Program interrupted")