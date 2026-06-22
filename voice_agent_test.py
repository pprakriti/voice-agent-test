import sys
import json
import asyncio
from dotenv import load_dotenv

class ScenarioData:
    def __init__(self, number, scenario):
        self.number = number
        self.scenario = scenario

    def __repr__(self):
        return f"ScenarioData(number={self.number}, scenario='{self.scenario}')"


async def execute_voice_test(scenario_obj):
    """ Test by making a call to agent and prompt the scneario"""
    print(f"\n------- Starting test case #{scenario_obj.number} -------\n")


    await asyncio.sleep(1)

    print(f"\n------- Finished testing #{scenario_obj.number} -------\n")


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


    #print(scenario_list)
    print(f"Going to run test scenarios: f{len(scenario_list)}")
    for testcase in scenario_list:
        await execute_voice_test(testcase)
        await asyncio.sleep(1)


if __name__ == "__main__":
    # run async as calls run async
    asyncio.run(main())
