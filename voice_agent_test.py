import sys
import json
import asyncio
from dotenv import load_dotenv

# for download recording
import urllib.request

from vapi import AsyncVapi
import os
from google import genai
from google.genai import types

class ScenarioData:
    def __init__(self, number, scenario):
        self.number = number
        self.scenario = scenario

    def __repr__(self):
        return f"ScenarioData(number={self.number}, scenario='{self.scenario}')"

async def execute_voice_test(vapi_client, gemini_client, scenario_obj):
    """ Test by making a call to agent and prompt the scneario"""

    print(f"\n------- Starting test case #{scenario_obj.number} -------\n")


    response = await vapi_client.calls.create(
                # which number is doing the dialing
                phone_number_id=os.getenv("VAPI_PHONE_ID"),

                # This is your personal number for testing
                customer={
                    #"number": "+16507014765"
                    "number": "+18054398008"
                },

                assistant={
                    "firstMessage": "Hello?",
                    "model": {
                        "provider": "openai",
                        "model": "gpt-4o-mini",
                        "messages": [
                            {
                                "role": "system",
                                "content": f"You are testing a medical AI. {scenario_obj.scenario}"
                            }
                        ]
                    },
                    "voice": {
                        "provider": "11labs",
                        "voiceId": "bIHbv24MWmeRgasZH58o"
                    }
                }
            )
    # call_id returned right away, need to poll for results
    call_id = response.id

    # poll for status
    call_data = await vapi_client.calls.get(call_id)

    # call can fail or error too
    while str(call_data.status) not in ['ended', 'failed', 'errored']:
        # sleep until call ended
        await asyncio.sleep(10)
        # Fetch the updated state for next loop iteration
        call_data = await vapi_client.calls.get(call_id)

    # call ended now but stitching takes time
    print("Call ended! Waiting 5 seconds for Vapi to generate the recording and transcript...")
    await asyncio.sleep(5)
    call_data = await vapi_client.calls.get(call_id)

    # use getattr extract using both camelCase and snake_cas without crashing, gives None
    transcript = getattr(call_data, 'transcript', "No transcript available.")
    recording_url = getattr(call_data, 'recordingUrl', getattr(call_data, 'recording_url', None))
    if not recording_url:
        print("Warning: no mp3 url found")

    # save transcript + recording mp3
    transcript_file = f"transcript_scenario_{scenario_obj.number}.txt"
    with open(transcript_file, "w") as f:
        if transcript:
            f.write(transcript)
        else:
            f.write("No transcript available")
    print(f"Saved: {transcript_file}")

    # recording fetch and save
    if recording_url:
        audio_file = f"audio_scenario_{scenario_obj.number}.mp3"
        print(f"Downloading audio from {recording_url}...")

        # helper function to inject the browser header
        def download_audio_with_headers(url, filename):
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(filename, 'wb') as out_file:
                out_file.write(response.read())
        # to_thread avoid synchronous download from blocking async event loop

        # safe download function in the background thread
        await asyncio.to_thread(download_audio_with_headers, recording_url, audio_file)
        print(f"Saved: {audio_file}")

    graded_response = await grade_reply(transcript, scenario_obj.scenario, gemini_client)
    print(f"\n------- Finished testing #{scenario_obj.number}, results: {graded_response} -------\n")


async def grade_reply(transcript, scenario, client):
    ''' Use gemini to evaluate the result '''
    prompt = f"""
        Review this transcript between an AI testing bot and a medical AI agent.
        The testing bot's goal was: {scenario}
        
        Transcript:
        {transcript}
        
        Output a JSON object with the following keys:
        - "goal_achieved": boolean
        - "bugs_found": list of strings
        - "brief_summary": string
        """

    response = await client.aio.models.generate_content(model='gemini-2.5-flash', contents=prompt, 
                                                        config=types.GenerateContentConfig(response_mime_type="application/json"))
    return response.text


async def main():
    # api keys load
    #load_dotenv()
    load_dotenv(override=True)
    # read the json and save the data
    if len(sys.argv) < 2:
        print(f"Pass test file name in json: current: {len(sys.argv) - 1}")
        sys.exit(1)



    scenario_list = []
    test_file = sys.argv[1]
    with open(test_file, "r") as file:
        test_data = json.load(file)

    for item in test_data:
        obj = ScenarioData(number=item["number"], scenario=item["scenario"])
        scenario_list.append(obj)

    vapi_client = AsyncVapi(token=os.getenv("VAPI_TOKEN"))

    # global key
    gemini_client = genai.Client(api_key=os.getenv("GEMINI_STUDIO_API_KEY"))

    #print(scenario_list)
    print(f"Going to run test scenarios: {len(scenario_list)}")
    for testcase in scenario_list:
        await execute_voice_test(vapi_client, gemini_client, testcase)
        await asyncio.sleep(1)


if __name__ == "__main__":
    # run async as calls run async
    asyncio.run(main())

