#!/usr/bin/env python3
# countasync.py

import asyncio
import datetime
import locale

import aiohttp

async def count():
    print("One")
    await asyncio.sleep(1)
    print("Two")

async def main():
    weather_api_key = 'bcde94c14bda17e23edce27c08a8192f'
    weather_city_id = '2754064' # lookup your city ID here: https://openweathermap.org/find
    url = f'https://api.openweathermap.org/data/2.5/weather?id={weather_city_id}&appid={weather_api_key}&units=metric&lang=nl'
    data = await make_request(url)
    await asyncio.gather(update_time())


async def update_time():
    current_time = datetime.datetime.now()
    print(f"Time is {(current_time.strftime("%H:%M:%S"))}")

async def make_request(url):
    # todo: retry after X time when it failed so use different var for self.main_app.settings.show_weather_on_idle when no connection
    # oooooor... just show the latest weather with a "no connection" icon in weather or maybe "last measured"?
    
    for i in range(3):
        try:
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                async with session.get(url) as response:
                    if response.status == 200:  # Check if the response is successful
                        data = await response.read()  # Read the response content asynchronously
                        print(f'Success getting weather.')
                        return data
                    else:
                        print(f'Error (aiohttp) calling {url}: HTTP RESPONSE: {response.status}')
        except aiohttp.ClientError as e:
            print(f'Error (aiohttp) calling {url}: {e}')
        except Exception as e:
            print(f'Error calling {url}: {e}')

        # Introduce a delay between retries
        print(f'Waiting for {1} seconds before retrying weather API again.')
        await asyncio.sleep(1)
    
    return None
    

if __name__ == "__main__":
    import time
    s = time.perf_counter()
    asyncio.run(main())
    elapsed = time.perf_counter() - s
    print(f"{__file__} executed in {elapsed:0.2f} seconds.")
