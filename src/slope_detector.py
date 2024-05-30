from typing import List
from enum import Enum
from data import Thresholds

class Direction(Enum):
    FALLING=-1
    SLIGHTLY_FALLING = -0.5
    STATIC=0
    SLIGHTLY_RISING = 0.5
    RISING=1

def get_direction(datapoint: float, positive_threshold: Thresholds, negative_treshold: Thresholds) -> Direction:
        if (datapoint > positive_threshold.value):
            return Direction.RISING
        elif (datapoint < negative_treshold.value):
            return Direction.FALLING
        elif (datapoint > 2):
             return Direction.SLIGHTLY_RISING
        elif (datapoint < -2):
             return Direction.SLIGHTLY_FALLING
        return Direction.STATIC

def detect_slope(dataset: List[float], positive_threshold: Thresholds, negative_treshold: Thresholds) -> Direction:
    if len(dataset) < 2: return Direction.STATIC
    differences = [dataset[i+1] - dataset[i] for i in range(len(dataset) - 1)]
    
    current_direction = get_direction(differences[-1], positive_threshold, negative_treshold)
    falling_count = 0
    rising_count = 0
    for difference in reversed(differences):
        cd = get_direction(difference, positive_threshold, negative_treshold).value
        if (cd < 0 and cd < current_direction.value):
            falling_count += 1
        elif (cd > 0 and cd > current_direction.value):
            rising_count += 1
        if (falling_count > (len(dataset) / 2)):
            current_direction = Direction.FALLING
            break
        if (rising_count > (len(dataset) / 2)):
            current_direction = Direction.RISING
            break

    return current_direction
