import random
from typing import List
from aerialist.px4.drone_test import DroneTest
from aerialist.px4.obstacle import Obstacle
from testcase import TestCase
import signal

def timeout_handler(signum, frame):
        raise Exception("Timeout")

class DeapGenerator(object):
    
    def __init__(self, case_study_file: str) -> None:
        self.case_study = DroneTest.from_yaml(case_study_file)

    def generate(self, budget: int, obstacles) -> List[TestCase]:
        test_cases = []
        for i in range(budget):
            test = TestCase(self.case_study, obstacles)
            try:
                signal.signal(signal.SIGALRM, timeout_handler)
                timeout_duration = 60 * 10
                signal.alarm(timeout_duration)

                test.execute()


                distances = test.get_distances()
                print(f"minimum_distance:{min(distances)}")
                test.plot()
                test_cases.append(test)
            except Exception as e:
                print("Exception during test execution, skipping the test")
                print(e)

        ### You should only return the test cases
        ### that are needed for evaluation (failing or challenging ones)
        return test_cases


if __name__ == "__main__":
    generator = DeapGenerator("case_studies/mission1.yaml")
    generator.generate(3)
