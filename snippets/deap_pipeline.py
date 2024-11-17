import os
import json
from deap_generator import DeapGenerator 
from deap import base, creator, tools  
from aerialist.px4.drone_test import DroneTest  
from aerialist.px4.obstacle import Obstacle  
import shutil
from decouple import config
from datetime import datetime

import random 
import yaml  

# ==============================
# CONFIGURATION AND LIMITS
# ==============================
LIMITS = {
    "x": (-40, 30),  # Limits for x position (min and max)
    "y": (10, 40),   # Limits for y position (min and max)
    "l": (10, 20),    # Limits for obstacle length (min and max)
    "w": (5, 5),    # Limits for obstacle width (min and max)
    "h": (25, 25),   # Fixed height for obstacles
    "r": (0, 0)     # Limits for obstacle rotation (degrees)
}

SAVE_FILE = "population_state_node88.json"  # File to save the population state for recovery
TESTS_FOLDER = config("TESTS_FOLDER", default="./generated_tests/")

tests_fld = f'{TESTS_FOLDER}{datetime.now().strftime("%d-%m-%H-%M-%S")}/'
os.mkdir(tests_fld)

n_generated_test = 0

mission = "case_studies/mission2.yaml"

# ==============================
# DEAP CONFIGURATION
# ==============================
# Change the fitness configuration to minimize the distance
creator.create("FitnessMin", base.Fitness, weights=(-1.0,))  # Negative weight for minimization
creator.create("Individual", list, fitness=creator.FitnessMin)

toolbox = base.Toolbox()

# Attribute generators for obstacle parameters (position, size, rotation)
toolbox.register("attr_x", lambda: random.uniform(LIMITS["x"][0], LIMITS["x"][1]))
toolbox.register("attr_y", lambda: random.uniform(LIMITS["y"][0], LIMITS["y"][1]))
toolbox.register("attr_l", lambda: random.uniform(LIMITS["l"][0], LIMITS["l"][1]))
toolbox.register("attr_w", lambda: random.uniform(LIMITS["w"][0], LIMITS["w"][1]))
toolbox.register("attr_h", lambda: random.uniform(LIMITS["h"][0], LIMITS["h"][1]))
toolbox.register("attr_r", lambda: random.uniform(LIMITS["r"][0], LIMITS["r"][1]))

# Define an individual as a cycle of 3 obstacles
toolbox.register("individual", tools.initCycle, creator.Individual,
                 (toolbox.attr_x, toolbox.attr_y, toolbox.attr_l, toolbox.attr_w, toolbox.attr_h, toolbox.attr_r),
                 n=3)

# Define a population as a list of individuals
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

# Register genetic operators: crossover, mutation, and selection
toolbox.register("mate", tools.cxTwoPoint)  # Two-point crossover
toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=5, indpb=0.2)  # Gaussian mutation
toolbox.register("select", tools.selTournament, tournsize=3)  # Tournament selection

# ==============================
# SAVE AND LOAD FUNCTIONS
# ==============================
def save_population(population, generation):
    """Save the current population and fitness values to a file for recovery."""
    data = {
        "generation": generation,
        "population": [
            {
                "genes": ind[:],  # Save individual's genes
                "fitness": ind.fitness.values[0] if ind.fitness.valid else None  # Save fitness if valid
            }
            for ind in population
        ]
    }
    with open(SAVE_FILE, "w") as file:
        json.dump(data, file, indent=4)  # Save as JSON with pretty formatting
    print(f"Saved population for generation {generation}.")

def load_population():
    """Load the population and fitness values from a file, if it exists."""
    if not os.path.exists(SAVE_FILE): 
        print("No save file found. Starting from scratch.")
        return None, 0  # Start fresh
    
    # Load JSON data from file
    with open(SAVE_FILE, "r") as file:
        data = json.load(file)  

    generation = data["generation"]  # generation number
    population = []

    for item in data["population"]:
        ind = creator.Individual(item["genes"])  # Recreate individual
        if item["fitness"] is not None:
            ind.fitness.values = (item["fitness"],)  # Restore fitness
        population.append(ind)

    print(f"Loaded population from generation {generation}.")
    return population, generation

# ==============================
# SUPPORT FUNCTIONS
# ==============================
def bound(value, lower, upper):
    """Ensure a value is within the specified bounds."""
    return max(min(value, upper), lower)

def check_no_overlap(obstacles):
    """Check that no obstacles overlap."""
    for i in range(len(obstacles)):
        for j in range(i + 1, len(obstacles)):
            a = obstacles[i]
            b = obstacles[j]
            
            # Extract position and size for both obstacles
            x_a, y_a, l_a, w_a = a.position.x, a.position.y, a.size.l, a.size.w
            x_b, y_b, l_b, w_b = b.position.x, b.position.y, b.size.l, b.size.w
            
            # Check overlap conditions on x and y axes
            no_overlap_x = (x_a + l_a / 2 <= x_b - l_b / 2) or (x_b + l_b / 2 <= x_a - l_a / 2)
            no_overlap_y = (y_a + w_a / 2 <= y_b - w_b / 2) or (y_b + w_b / 2 <= y_a - w_a / 2)
            
            if not (no_overlap_x and no_overlap_y):
                return False  # Overlap detected
    return True

def check_oub(obstacles):
    for i in range(len(obstacles)):
        obs = obstacles[i]
        if (obs.position.x - (obs.size.l  / 2 )) < LIMITS["x"][0]:
            return False
        if (obs.position.x + (obs.size.l  / 2 )) > LIMITS["x"][1]:
            return False
        if (obs.position.y - (obs.size.w  / 2 )) < LIMITS["y"][0]:
            return False
        if (obs.position.y + (obs.size.w  / 2 )) > LIMITS["y"][1]:
            return False
    return True

def decode_individual_to_obstacles(individual):
    """Convert an individual's genes into a list of obstacle objects."""
    list_obstacles = []
    for i in range(0, len(individual), 6):
        # Extract and bound obstacle parameters
        x = bound(individual[i], LIMITS["x"][0], LIMITS["x"][1])
        y = bound(individual[i+1], LIMITS["y"][0], LIMITS["y"][1])
        l = bound(individual[i+2], LIMITS["l"][0], LIMITS["l"][1])
        w = bound(individual[i+3], LIMITS["w"][0], LIMITS["w"][1])
        h = bound(individual[i+4], LIMITS["h"][0], LIMITS["h"][1])
        r = bound(individual[i+5], LIMITS["r"][0], LIMITS["r"][1])

        
        # Create obstacle object
        position = Obstacle.Position(x=x, y=y, z=0, r=r)
        size = Obstacle.Size(l=l, w=w, h=h)
        obstacle = Obstacle(size, position)
        
        # Ensure no overlaps
        max_attempts = 10
        attempts = 0
        while attempts < max_attempts and any(not check_no_overlap([obstacle, o]) for o in list_obstacles):
            x = random.uniform(LIMITS["x"][0], LIMITS["x"][1])
            y = random.uniform(LIMITS["y"][0], LIMITS["y"][1])
            position = Obstacle.Position(x=x, y=y, z=0, r=r)
            obstacle = Obstacle(size, position)
            attempts += 1
        list_obstacles.append(obstacle)

    return list_obstacles

def evaluate(individual):
    """Evaluate an individual based on the minimum distance to obstacles."""
    obstacles = decode_individual_to_obstacles(individual)

    # Check for overlaps
    if not check_no_overlap(obstacles):
        print("Overlap detected. Maximum penalty assigned.")
        return 100.0,  # Penalize heavily for overlapping obstacles

    if not check_oub(obstacles):
        print("Out of bound detected. Maximum penalty assigned.")
        return 100.0,  # Penalize heavily for overlapping obstacles

    # Generate test cases with obstacles
    generator = DeapGenerator(mission)
    print(f'Running simulation... {datetime.now().strftime("%d-%m-%H-%M-%S")}')
    test_cases = generator.generate(1, obstacles)
    if not test_cases:
        print("No test case generated. Maximum penalty assigned.")
        return 100.0,  # Penalize heavily if no test cases are generated

    # tests_fld = f'{TESTS_FOLDER}{datetime.now().strftime("%d-%m-%H-%M-%S")}/'
    # os.mkdir(tests_fld)
    global n_generated_test
    for i in range(len(test_cases)):
        test_cases[i].save_yaml(f"{tests_fld}/test_{n_generated_test}.yaml")
        shutil.copy2(test_cases[i].log_file, f"{tests_fld}/test_{n_generated_test}.ulg")
        shutil.copy2(test_cases[i].plot_file, f"{tests_fld}/test_{n_generated_test}.png")
        n_generated_test += 1

    # Calculate the minimum distance across all test cases
    min_distances = [min(tc.get_distances()) for tc in test_cases]
    if not min_distances:
        return 100.0,  # Penalize if distances are invalid or not computed

    min_distance = min(min_distances)
    print(f"Minimum distance: {min_distance:.2f}m")
    return min_distance,  # Lower is better for minimization

toolbox.register("evaluate", evaluate)

# ==============================
# MAIN PIPELINE
# ==============================
if __name__ == "__main__":

    POPULATION = 200
    generations = 1000  # Number of generations
    cxpb = 0.5  # Crossover probability
    mutpb = 0.2  # Mutation probability

    # Load existing population or start fresh
    population, start_generation = load_population()
    if population is None:
        # Generate initial population
        population = toolbox.population(n=POPULATION)  
        start_generation = 0

    for gen in range(start_generation, generations):
        print(f"\n==== Generation {gen+1}/{generations} ====")
        
        # Evaluate fitness for the population
        fitnesses = list(map(toolbox.evaluate, population))
        for ind, fit in zip(population, fitnesses):
            ind.fitness.values = fit

        # Log average fitness
        avg_fitness = sum(ind.fitness.values[0] for ind in population) / len(population)
        print(f"Average fitness (lower is better): {avg_fitness:.4f}")
        save_population(population, gen + 1)  # Save progress

        # Perform genetic operations: selection, crossover, mutation
        offspring = toolbox.select(population, len(population))  # Select offspring
        offspring = list(map(toolbox.clone, offspring))  # Clone selected offspring
        
        for child1, child2 in zip(offspring[::2], offspring[1::2]):
            if random.random() < cxpb:
                toolbox.mate(child1, child2)  # Apply crossover
                del child1.fitness.values  # Reset fitness after crossover
                del child2.fitness.values
        
        for mutant in offspring:
            if random.random() < mutpb:
                toolbox.mutate(mutant)  # Apply mutation
                del mutant.fitness.values  # Reset fitness after mutation
        
        population[:] = offspring  # Replace the population with offspring

    # Get the best individual after all generations
    best_individual = tools.selBest(population, k=1)[0]
    best_obstacles = decode_individual_to_obstacles(best_individual)

    print("\n=== Final Result ===")
    print(f"Best configuration: {best_obstacles}")
    print(f"Best fitness (minimum distance): {best_individual.fitness.values[0]:.4f}")
