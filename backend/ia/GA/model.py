from numba import njit, prange
import numpy as np
from .utils import nearest_neighbor, route_distance, two_opt


def init_population(
    population_size: int, seed_route: list[int], use_seed=True
) -> np.ndarray:
    n_genes = len(seed_route)
    population = np.zeros((population_size, n_genes), dtype=np.int32)
    if use_seed:
        population[0] = seed_route
        for i in range(1, population_size):
            mutated = seed_route.copy()
            i1, i2 = sorted(np.random.choice(n_genes, size=2, replace=False))
            mutated[i1 : i2 + 1] = mutated[i1 : i2 + 1][::-1]
            population[i] = mutated
    else:
        for i in range(population_size):
            population[i] = np.random.permutation(n_genes)

    return population


@njit(parallel=True)
def tournament_selection(
    population: np.ndarray, dist_matrix: np.ndarray, k: int = 3
) -> tuple[np.ndarray, np.ndarray]:
    population_size = len(population)
    num_winners = population_size // 2

    fitness = np.empty(population_size, dtype=np.float64)
    for i in prange(population_size):
        fitness[i] = route_distance(population[i], dist_matrix)

    winners = np.empty(num_winners, dtype=np.int32)
    winners_fitness = np.empty(num_winners, dtype=np.float64)

    for i in prange(num_winners):
        indices = np.random.choice(
            population_size, size=min(k, population_size), replace=False
        )
        winner = indices[np.argmin(fitness[indices])]
        winners[i] = winner
        winners_fitness[i] = fitness[winner]

    return population[winners], winners_fitness


@njit
def crossover(parent1: np.ndarray, parent2: np.ndarray) -> np.ndarray:
    n = parent1.shape[0]
    i1 = np.random.randint(0, n)
    i2 = np.random.randint(0, n)
    if i1 > i2:
        i1, i2 = i2, i1

    child = -np.ones(n, dtype=np.int32)
    child[i1 : i2 + 1] = parent1[i1 : i2 + 1]

    n_free = n - (i2 - i1 + 1)
    free_pos = np.empty(n_free, dtype=np.int32)
    fp_idx = 0

    for j in range(n):
        if child[j] == -1:
            free_pos[fp_idx] = j
            fp_idx += 1

    fp_idx = 0
    for j in range(n):
        gene = parent2[j]

        present = False
        for k in range(i1, i2 + 1):
            if parent1[k] == gene:
                present = True
                break
        if not present:
            child[free_pos[fp_idx]] = gene
            fp_idx += 1

    return child


@njit
def mutate(route: np.ndarray) -> np.ndarray:
    i, j = sorted(np.random.choice(len(route), size=2, replace=False))
    route[i : j + 1] = route[i : j + 1][::-1]
    return route


def genetic_algorithm(
    points: list,
    origin: tuple,
    population_size: int = 100,
    generations: int = 1000,
    mutation_rate: float = 0.2,
    early_stop=True,
    seeding=True,
    post_process=True,
    initial=False,
) -> tuple[list[int], float]:

    nn_route, dist_matrix = nearest_neighbor(origin, np.array(points), initial=initial)
    population = init_population(population_size, nn_route, use_seed=seeding)
    improvement_threshold = 0.001 if early_stop else -1
    best_route, best_distance = _ga_core(
        population, dist_matrix, generations, mutation_rate, 250, improvement_threshold
    )
    if post_process:
        best_route = two_opt(best_route, dist_matrix, max_iterations=1000)
        best_distance = route_distance(best_route, dist_matrix)
    return best_route, best_distance


@njit
def _ga_core(
    population: np.ndarray,
    dist_matrix: np.ndarray,
    generations: int,
    mutation_rate: float,
    window_size: int,
    improvement_thresh: float,
) -> tuple[np.ndarray, float]:

    n_pop, n_genes = population.shape
    best_route = np.empty(n_genes, dtype=np.int32)
    best_distance = np.inf

    history = np.empty(window_size, dtype=np.float64)
    hist_idx = 0
    filled = 0
    pop = population.copy()

    for _ in range(generations):

        selecteds, fitness = tournament_selection(pop, dist_matrix)

        elite_idx = np.argmin(fitness)
        elite = selecteds[elite_idx]
        elite_fitness = fitness[elite_idx]

        if elite_fitness < best_distance:
            best_route[:] = elite
            best_distance = elite_fitness

        history[hist_idx] = best_distance
        hist_idx = (hist_idx + 1) % window_size
        filled = min(filled + 1, window_size)
        if filled == window_size:
            oldest = history[hist_idx]
            rel_improve = (oldest - best_distance) / oldest
            if rel_improve < improvement_thresh:
                break

        new_population = np.empty_like(pop)
        new_population[0] = two_opt(elite, dist_matrix, max_iterations=1)

        n = len(selecteds)
        for i in range(1, n_pop, 2):
            j = np.random.randint(n)
            k = np.random.randint(n - 1)
            if k >= j:
                k += 1
            parent1, parent2 = selecteds[j], selecteds[k]

            child1 = crossover(parent1, parent2)
            if np.random.rand() < mutation_rate:
                child1 = mutate(child1)
            new_population[i] = child1

            if i + 1 < n_pop:
                child2 = crossover(parent2, parent1)
                if np.random.rand() < mutation_rate:
                    child2 = mutate(child2)
                new_population[i + 1] = child2

        pop = new_population

    return best_route, best_distance
