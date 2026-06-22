import sys
import json
import asyncio
from dotenv import load_dotenv

# for download recording
import urllib.request

from vapi import AsyncVapi
import os
import google.generativeai as genai

class ScenarioData:
    def __init__(self, number, scenario):
        self.number = number
        self.scenario = scenario

    def __repr__(self):
        return f"ScenarioData(number={self.number}, scenario='{self.scenario}')"

async def execute_voice_test(vapi_client, gemini_model, scenario_obj):
    """ Test by making a call to agent and prompt the scneario"""

    print(f"\n------- Starting test case #{scenario_obj.number} -------\n")


    response = await vapi_client.calls.create(
            assistant={
                "firstMessage": "Hello?", # Gets the target AI to start talking
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
                    "voiceId": "bIHbv24MWmeRgasZH58o" # A default voice
                    }
                },
            customer={
                "number": "+18054398008"
                }
            )
    # call_id returned right away, need to poll for results
    call_id = response.id

    # poll for status
    call_data = await vapi_client.calls.get(call_id)

    # call can fail or error too
    while call_data.status not in ['ended', 'failed', 'errored']:
        # sleep until call ended
        await asyncio.sleep(10)
        # Fetch the updated state for next loop iteration
        call_data = await vapi_client.calls.get(call_id)

    # call ended now
    transcript = call_data.transcript
    recording_url = call_data.recording_url

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

        # to_thread avoid synchronous download from blocking async event loop

        await asyncio.to_thread(urllib.request.urlretrieve, recording_url, audio_file)
        print(f"Saved: {audio_file}")

    graded_response = await grade_reply(transcript, scenario_obj.scenario, gemini_model)
    print(f"\n------- Finished testing #{scenario_obj.number}, results: {graded_response} -------\n")


async def grade_reply(transcript, scenario, model):
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

    response = await model.generate_content_async(prompt, generation_config={"response_mime_type": "application/json"})

    return response.text


async def main():
    # api keys load
    load_dotenv()
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

    vapi_client = AsyncVapi(api_key=os.getenv("VAPI_TOKEN"))

    # global key
    genai.configure(api_key=os.getenv("GEMINI_STUDIO_API_KEY"))
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')

    #print(scenario_list)
    print(f"Going to run test scenarios: {len(scenario_list)}")
    for testcase in scenario_list:
        await execute_voice_test(vapi_client, gemini_model, testcase)
        await asyncio.sleep(1)


if __name__ == "__main__":
    # run async as calls run async
    asyncio.run(main())

