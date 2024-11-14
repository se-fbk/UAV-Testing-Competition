import random
from typing import List
from math import cos, sin, pi

import config
from aerialist.px4.drone_test import DroneTest
from aerialist.px4.obstacle import Obstacle
from testcase import TestCase

from obstacle_generator import ObstacleGenerator
import json

from datetime import datetime
import os
import shutil
import multiprocessing


class CompetitionGenerator(object):

    def __init__(self, case_study_file: str) -> None:
        self.case_study = DroneTest.from_yaml(case_study_file)
        self.case_study_file = case_study_file

    def run_test(self, test: TestCase) -> None:
        test.execute()

    def generate(self, budget: int) -> List[TestCase]:


        tests_fld = f'{config.TESTS_FOLDER}{os.path.basename(self.case_study_file).replace(".yaml","")}_{datetime.now().strftime("%d-%m-%H-%M-%S")}/'
        print(f'{datetime.now().strftime("%d-%m-%H-%M-%S")} Save tests in folder {tests_fld}')
        os.mkdir(tests_fld)
        n_gen_test = 0
        min_distance = 10

        test_cases = []
        for _ in range(budget):
          
            obstacle_generator = ObstacleGenerator()
            obstacles = obstacle_generator.generate(self.case_study_file)
            print(json.dumps(obstacles, indent=4))

            list_obstacles = []
            for obst in obstacles:
                
                position = Obstacle.Position(
                    x=obst['x'], 
                    y=obst['y'], 
                    z=0,
                    r=0,
                    #r=obst['r'],
                )

                size = Obstacle.Size(
                    l=obst['length'], 
                    w=obst['width'], 
                    h= config.OBSTACLE_HEIGHT, # Fixed height of the obstacle
                )
                
                # Create an obstacle with size and position
                obstacle = Obstacle(size, position)
                list_obstacles.append(obstacle)

            test = TestCase(self.case_study, list_obstacles)
            try:
                # Execute test case in a separated thread with a timeout
                print(f'{datetime.now().strftime("%d-%m-%H-%M-%S")} Starting test')
                p = multiprocessing.Process(target=self.run_test,  args= (test,)  )
                p.start()
                p.join(timeout=config.TIMEOUT_MAX)
                if p.is_alive():
                    p.terminate()  # Forcefully terminate the process
                    print(f'{datetime.now().strftime("%d-%m-%H-%M-%S")} Test execution timed out')
                    # test.execute()
                else:
                    distances = test.get_distances()
                    print(f'{datetime.now().strftime("%d-%m-%H-%M-%S")} Minimum_distance: {min(distances)}')

                    # save if distances is less than min_distance
                    if min(distances) < config.MIN_DISTANCE_TO_SAVE:
                        print(f'{datetime.now().strftime("%d-%m-%H-%M-%S")} Saving test {n_gen_test + 1}')
                        test.plot()
                        test.save_yaml(f"{tests_fld}/test_{n_gen_test}.yaml")
                        shutil.copy2(test.log_file, f"{tests_fld}/test_{n_gen_test}.ulg")
                        shutil.copy2(test.plot_file, f"{tests_fld}/test_{n_gen_test}.png")
                        n_gen_test += 1
                        test_cases.append(test)

            except Exception as e:
                print("Exception during test execution, skipping the test")
                print(e)
        
        return test_cases

if __name__ == "__main__":
    # Testing
    generator = CompetitionGenerator("case_studies/mission3.yaml")
    generator.generate(3) # Budget
