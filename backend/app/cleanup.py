"""Transparent additive cleanup proxy and bounded exact binary portfolio.

Default policy uses capped source screening counts only. Unknown positively
weighted evidence makes the score unavailable, not zero; weights are never
renormalized over available fields. No atmospheric simulations run here.
"""
from collections import Counter
from datetime import UTC,datetime,timedelta
import math

import numpy as np
from scipy.optimize import Bounds,LinearConstraint,milp

from app.data.celestrak import validate_object_id
from app.data.metadata import MetadataUnavailable
from app.data.socrates import SourceUnavailable
from app.models.cleanup import (CleanupCandidate,CleanupConstraints,CleanupPortfolio,
    PersistenceEvidence,PriorityPolicy,PriorityScore)


def screening_exposure(dataset,now=None):
    now = now or datetime.now(UTC)
    indexed = {}
    seen = set()
    times = []
    if dataset is None: return indexed,{"status":"UNAVAILABLE","warnings":["No screening dataset; unknown counts are not zero"]}
    for event in dataset.encounters:
        if event.time_of_closest_approach < now: continue
        ids = tuple(sorted((validate_object_id(event.object_1_id),validate_object_id(event.object_2_id))))
        key = (*ids,event.time_of_closest_approach)
        if key in seen: continue
        seen.add(key)
        times.append(event.time_of_closest_approach)
        for identifier in ids:
            stats = indexed.setdefault(identifier,{"count":0,"encounter_ids":[],"minimum_source_miss_distance_m":None,
                "maximum_socrates_screening_metric":None})
            stats["count"] += 1
            stats["encounter_ids"].append(event.id)
            old = stats["minimum_source_miss_distance_m"]
            stats["minimum_source_miss_distance_m"] = event.source_miss_distance_m if old is None else min(old,event.source_miss_distance_m)
            metric = event.socrates_max_probability
            if metric is not None:
                old = stats["maximum_socrates_screening_metric"]
                stats["maximum_socrates_screening_metric"] = metric if old is None else max(old,metric)
    return indexed,{"status":dataset.data_status,"source_url":dataset.source_url,
        "content_sha256":dataset.content_sha256,"dataset_timestamp":dataset.dataset_timestamp.isoformat(),
        "fetched_at":dataset.fetched_at.isoformat(),"upcoming_unique_encounters":len(seen),
        "tca_start":min(times).isoformat() if times else None,"tca_end":max(times).isoformat() if times else None,
        "selection_start":now.isoformat(),"limitations":["Published predicted screening events, not observed collisions or a complete long-term collision frequency.",
        "No matches means no published matches within this limited snapshot/window, not zero actual risk.",
        "SOCRATES MAX_PROB is retained separately and is not covariance-based Pc or a priority probability."]}


def build_candidates(records,metadata,dataset,persistence=None,now=None):
    now = now or datetime.now(UTC)
    indexed,coverage = screening_exposure(dataset,now)
    persistence = persistence or {}
    unique = {}
    for orbit in records:
        identifier = validate_object_id(orbit.elements.object_id)
        if identifier not in unique or orbit.elements.epoch > unique[identifier].elements.epoch:
            unique[identifier] = orbit
    result = []
    for identifier,orbit in sorted(unique.items(),key=lambda item:int(item[0])):
        meta = None if metadata is None else metadata.records.get(identifier)
        reason = "No reliable object-type metadata; classification unknown" if meta is None else meta.eligibility_reason
        if abs((now-orbit.elements.epoch).total_seconds()) > 7*86400:
            reason = "GP epoch exceeds the seven-day current-assessment limit"
        evidence = persistence.get(identifier)
        if evidence is not None and abs((now-evidence.initial_epoch).total_seconds()) > 86400:
            evidence = None
        stats = indexed.get(identifier,{"count":0,"encounter_ids":[],"minimum_source_miss_distance_m":None,
            "maximum_socrates_screening_metric":None}) if dataset is not None else {
            "count":None,"encounter_ids":[],"minimum_source_miss_distance_m":None,"maximum_socrates_screening_metric":None}
        rcs = None if meta is None else meta.radar_cross_section_m2
        result.append(CleanupCandidate(id=identifier,name=orbit.elements.object_name,
            classification="UNKNOWN" if meta is None else meta.classification,eligible=reason is None,
            eligibility_reason=reason,element_epoch=orbit.elements.epoch,inclination_deg=orbit.elements.inclination_deg,
            orbit_metadata={"source":"GP mean elements; SATCAT altitude metadata is not a propagated state",
                "mean_motion_rev_day":orbit.elements.mean_motion_rev_day,"eccentricity":orbit.elements.eccentricity,
                "satcat_apogee_km":None if meta is None else meta.apogee_km,
                "satcat_perigee_km":None if meta is None else meta.perigee_km,
                "altitude_timestamp":None if meta is None else meta.provenance["dataset_timestamp"]},
            screening_exposure=stats,persistence=evidence,
            physical_metadata={"mass_kg":None,"dimensions_m":None,"aerodynamic_area_m2":None,"radar_cross_section_m2":rcs,
                "radar_cross_section_is_not_aerodynamic_area":True},
            missing_data=["mass_kg","dimensions_m","aerodynamic_area_m2"]+(["persistence"] if evidence is None else [])+(["radar_cross_section_m2"] if rcs is None else []),
            provenance={"gp_url":orbit.source_url,"gp_sha256":orbit.content_sha256,"gp_fetched_at":orbit.fetched_at.isoformat(),
                "gp_data_status":orbit.data_status,"object_type":None if meta is None else meta.model_dump(mode="json")},
            warnings=[*orbit.warnings,"Removal feasibility, physical properties and mission costs are not established."] ))
    return result,coverage


def calculate_priorities(candidates,policy=None):
    policy = policy or PriorityPolicy()
    weights = {"screening_exposure":policy.exposure_weight,"modeled_persistence":policy.persistence_weight,
        "radar_cross_section":policy.radar_cross_section_weight}
    total = sum(weights.values())
    result = {}
    for candidate in candidates:
        count = candidate.screening_exposure["count"]
        days = None if candidate.persistence is None else candidate.persistence.modeled_duration_days
        rcs = candidate.physical_metadata["radar_cross_section_m2"]
        values = {"screening_exposure":None if count is None else min(1,count/policy.exposure_saturation_count),
            "modeled_persistence":None if days is None else min(1,days/policy.persistence_saturation_days),
            "radar_cross_section":None if rcs is None else min(1,math.log1p(rcs)/math.log1p(policy.radar_cross_section_saturation_m2))}
        components = {name:{"value":value,"weight":weights[name]/total,
            "contribution":None if value is None and weights[name] else (value or 0)*weights[name]/total,
            "status":"UNAVAILABLE" if value is None else "AVAILABLE"} for name,value in values.items()}
        unknown = [name for name,value in values.items() if value is None and weights[name] > 0]
        lower = sum((value or 0)*weights[name]/total for name,value in values.items())
        upper = lower+sum(weights[name]/total for name in unknown)
        result[candidate.id] = PriorityScore(id=candidate.id,score=None if unknown or not candidate.eligible else lower,
            score_interval=(lower,min(1,upper)),status="INELIGIBLE" if not candidate.eligible else "INSUFFICIENT_EVIDENCE" if unknown else "RANKABLE",
            components=components,reasons=([candidate.eligibility_reason] if not candidate.eligible else [])+
            (["Positively weighted evidence missing: "+", ".join(unknown)] if unknown else []))
    return result


def optimize_cleanup_portfolio(candidate_objects,constraints=None,priorities=None,*,policy=None,coverage=None):
    constraints = constraints or CleanupConstraints()
    policy = policy or PriorityPolicy()
    unique = {c.id:c for c in candidate_objects}
    if len(unique) > constraints.max_candidates:
        raise ValueError("Candidate count exceeds the explicit portfolio workload bound")
    candidates = list(unique.values())
    priorities = priorities or calculate_priorities(candidates,policy)
    if set(priorities) != set(unique):
        raise ValueError("Priority records must match the unique candidate IDs")
    ranking = sorted(priorities.values(),key=lambda s:(s.score is None,-(s.score or 0),int(s.id)))
    excluded = {}
    available = []
    effort = constraints.effort_costs
    for score in ranking:
        reasons = list(score.reasons)
        if score.id in constraints.excluded_ids: reasons.append("Explicit user exclusion")
        if effort is not None and score.id not in effort: reasons.append("User-supplied abstract effort cost missing")
        if reasons or score.status != "RANKABLE": excluded[score.id] = reasons or [score.status]
        else: available.append(score)
    warnings = []
    status = "OPTIMAL_WITHIN_CANDIDATE_POOL"
    if constraints.max_targets == 0 or constraints.effort_budget == 0:
        selected = []
    elif effort is None or constraints.effort_budget is None:
        selected = available[:constraints.max_targets]
    elif available:
        costs = np.array([effort[s.id] for s in available])
        scores = np.array([s.score for s in available])
        solution = milp(-scores,integrality=np.ones(len(scores)),bounds=Bounds(0,1),
            constraints=LinearConstraint(np.vstack([np.ones(len(scores)),costs]),[0,0],
                [constraints.max_targets,constraints.effort_budget]),
            options={"time_limit":constraints.solver_timeout_seconds,"mip_rel_gap":0})
        if solution.x is None:
            selected,status = [],"UNAVAILABLE"
            warnings.append(f"No verified feasible portfolio returned: {solution.message}")
        else:
            selected = [s for s,value in zip(available,solution.x) if value > .5]
            if solution.status != 0:
                status = "PARTIAL"
                warnings.append(f"Bounded solver did not establish optimality: {solution.message}")
    else: selected = []
    spent = math.fsum(effort[s.id] if effort is not None else 1 for s in selected)
    if len(selected) > constraints.max_targets or (constraints.effort_budget is not None and spent > constraints.effort_budget):
        raise ValueError("Solver result violates resource constraints; no invalid portfolio returned")
    if not available and candidates and constraints.max_targets:
        status = "UNAVAILABLE"
    chosen = [unique[s.id] for s in selected]
    events = Counter(identifier for c in chosen for identifier in c.screening_exposure["encounter_ids"])
    return CleanupPortfolio(status=status,selected_objects=chosen,priority_ranking=ranking,candidates=candidates,
        total_priority_proxy=math.fsum(s.score for s in selected),resource_model="TARGET_COUNT" if effort is None else "USER_SUPPLIED_ABSTRACT_EFFORT",
        targets_remaining=constraints.max_targets-len(chosen),total_abstract_resource_expenditure=spent,
        budget_remaining=None if constraints.effort_budget is None else constraints.effort_budget-spent,
        excluded_objects=excluded,unique_screening_encounters_represented=len(events),
        selection_reasons={s.id:f'Eligible and rankable; additive proxy {s.score:.6g}; selected within the declared candidate pool and resource constraints ({status})' for s in selected},
        shared_screening_encounter_ids=sorted(k for k,v in events.items() if v > 1),policy=policy,constraints=constraints,
        coverage=coverage or {},model_assumptions=["ILLUSTRATIVE POLICY CHOICE — additive priority proxy, not a mission plan or scientifically universal weighting.",
            "Exposure=min(count/saturation,1); persistence=min(modeled days/saturation,1); RCS=min(log1p(RCS)/log1p(saturation),1).",
            "Weights normalized once across configured criteria, not renormalized over available metadata; missing positively weighted evidence is unrankable, not zero.",
            "Data quality controls eligibility/comparability and is disclosed, never a bonus for more metadata.",
            "Persistence is explicitly modeled/censored scenario evidence, never inferred infinite lifetime or an observed reentry date.",
            "Shared source conjunctions can contribute to both object priorities, but this additive proxy is NOT independently prevented collisions; unique/shared event identities are reported.",
            "Abstract effort units are user-provided, not dollars, removal feasibility or estimated mission cost.",
            "Fixed-count selection sorts genuine scores; effort selection uses bounded binary HiGHS MILP and verifies actual resource sums."],warnings=warnings)


def record_persistence_evidence(engine,result):
    with engine._evidence_lock:
        _record_persistence_evidence(engine,result)


def _record_persistence_evidence(engine,result):
    engine.persistence_evidence.pop(result.object_id,None)
    if result.scenario_analysis is None: return
    nominal = next((s for s in result.scenario_analysis.scenarios if s.scenario == "NOMINAL"),None)
    if nominal is None or nominal.boundary.propagation is None: return
    boundary = nominal.boundary
    curve = boundary.propagation
    days = (curve.integrated_end_time-curve.start_time).total_seconds()/86400
    engine.persistence_evidence[result.object_id] = PersistenceEvidence(object_id=result.object_id,
        initial_epoch=result.initial_state.timestamp,modeled_duration_days=days,horizon_days=result.prediction_horizon_days,
        boundary_status=boundary.prediction_status,censored_at_horizon=not boundary.crossing_occurred,
        provenance={"gp":result.provenance,"weather_treatment":nominal.environment_assumptions,
            "physical_assumptions":nominal.aerodynamic_properties.model_dump(mode="json")},
        warnings=[*result.warnings,*boundary.warnings])
    while len(engine.persistence_evidence) > 256: engine.persistence_evidence.popitem(last=False)


def analyze_cleanup(engine,constraints=None,policy=None,candidate_ids=None,now=None):
    now = now or datetime.now(UTC)
    constraints,policy = constraints or CleanupConstraints(),policy or PriorityPolicy()
    catalog = engine.public_catalog()
    warnings = []
    try: metadata = engine.metadata.load()
    except MetadataUnavailable as error:
        metadata = None
        warnings.append(str(error))
    try: dataset = engine.socrates.get_dataset()
    except SourceUnavailable as error:
        dataset = None
        warnings.append(str(error))
    if candidate_ids is not None:
        ids = list(dict.fromkeys(validate_object_id(i) for i in candidate_ids))
        if len(ids) > constraints.max_candidates: raise ValueError("Requested IDs exceed max_candidates")
        records = [catalog.records[i] for i in ids if i in catalog.records]
        missing = {i:["Not available in selected public GP catalog"] for i in ids if i not in catalog.records}
        truncated = 0
    else:
        eligible = [record for i,record in catalog.records.items() if metadata is not None and
            i in metadata.records and metadata.records[i].eligibility_reason is None]
        records = sorted(eligible,key=lambda r:int(r.elements.object_id))[:constraints.max_candidates]
        truncated = max(0,len(eligible)-len(records))
        missing = {}
        if truncated: warnings.append("Candidate pool truncated by workload bound, stable NORAD-ID order; not a global ranking of all debris. Supply explicit candidate_ids to choose assessment scope.")
    with engine._evidence_lock: evidence=dict(engine.persistence_evidence)
    candidates,screening = build_candidates(records,metadata,dataset,evidence,now)
    coverage = {"catalog":catalog.metadata.model_dump(mode="json"),"screening":screening,
        "classification":None if metadata is None else metadata.provenance,"candidate_pool_truncated":truncated,
        "scope":"Explicit selected IDs" if candidate_ids is not None else "Bounded eligible public catalog subset, ascending NORAD ID"}
    result = optimize_cleanup_portfolio(candidates,constraints,policy=policy,coverage=coverage)
    result.excluded_objects.update(missing)
    result.warnings.extend(warnings)
    if metadata is not None: result.warnings.extend(metadata.warnings)
    if not catalog.records or metadata is None or dataset is None: result.status = "UNAVAILABLE"
    return result
