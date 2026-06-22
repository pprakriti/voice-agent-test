import sys
import json
import asyncio
from dotenv import load_dotenv

from vapi import AsyncVapi
import os
import google.generativeai as genai

vapi_client = None
gemini_client = None

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
                "number": "+1-805-439-8008"
                }
            )
    # call_id returned right away, need to poll for results
    call_id = response.id

    # poll for status
    while (await vapi_client.calls.get(call_id).status !='ended'):
        await asyncio.sleep(10)

    # call ended now

    transcript = response.transcript


    graded_response = await grade_reply(transcript, scenario_obj)
    print(f"\n------- Finished testing #{scenario_obj.number}, results: {graded_response} -------\n")


async def grade_reply(transcript, scenario):
    ''' Use gemini to evaluate the result '''
    model = genai.GenerativeModel('gemini-1.5-flash')
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

    response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})

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

    if vapi_client is None:
        vapi_client = AsyncVapi(api_key=os.getenv("VAPI_TOKEN"))

    if gemini_client is None:
        gemini_client = genai.configure(api_key=os.getenv("GEMINI_STUDIO_API_KEY"))

    #print(scenario_list)
    print(f"Going to run test scenarios: f{len(scenario_list)}")
    for testcase in scenario_list:
        await execute_voice_test(vapi_client, gemini_client, testcase)
        await asyncio.sleep(1)


if __name__ == "__main__":
    # run async as calls run async
    asyncio.run(main())
