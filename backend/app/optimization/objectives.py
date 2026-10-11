"""Transparent objective ordering without hidden danger or penalty scores."""

from app.models.maneuver import Objective


def objective_key(solution, objective: Objective):
    if objective == Objective.MINIMUM_DELTA_V:
        return (solution.delta_v_m_s, -solution.new_miss_distance_m, solution.maneuver_time,
                solution.delta_v_rtn_m_s)
    return (-solution.new_miss_distance_m, solution.delta_v_m_s, solution.maneuver_time,
            solution.delta_v_rtn_m_s)
