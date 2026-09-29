# CMS-2567 POC Adjudication Pilot

This pilot adjudicates plan-of-correction adequacy from visible text only. The
adjudicators do not see correction status or correction date; those fields are
used only for later sanity checks.

## Setup

- Input: `outputs/cms2567_poc_adjudication/cms2567_poc_sample_120.jsonl`
- Primary model: `gpt-5.4-mini`
- Audit model: ``
- Rubric version: `calibrated`
- Rows: 120
- Estimated cost before run: 0.576548 USD

## Label Distribution

- Primary labels: {'adequate': 28, 'inadequate': 10, 'partial': 82}
- Audit labels: {}
- Primary binary labels: {'adequate': 28, 'not_adequate': 92}
- Binary primary/audit agreement: None
- Three-way primary/audit agreement: None
- Mean primary confidence: 0.9228
- Median days to correction by primary binary: {'adequate': 35, 'not_adequate': 36}

## By Severity Band

```json
{
  "actual_harm": {
    "adequate": 5,
    "partial": 20,
    "inadequate": 3
  },
  "immediate_jeopardy": {
    "inadequate": 3,
    "partial": 24,
    "adequate": 3
  },
  "low_severity": {
    "adequate": 7,
    "partial": 6,
    "inadequate": 1
  },
  "potential_harm": {
    "inadequate": 3,
    "adequate": 13,
    "partial": 32
  }
}
```

## By F-Tag Group

```json
{
  "abuse_neglect": {
    "partial": 18,
    "adequate": 1,
    "inadequate": 2
  },
  "care_planning_records": {
    "adequate": 4,
    "partial": 8
  },
  "food_safety": {
    "adequate": 2,
    "partial": 7
  },
  "infection_control": {
    "inadequate": 2,
    "partial": 7,
    "adequate": 2
  },
  "other": {
    "partial": 18,
    "adequate": 8,
    "inadequate": 1
  },
  "resident_care_safety": {
    "inadequate": 5,
    "partial": 12,
    "adequate": 4
  },
  "resident_rights": {
    "adequate": 7,
    "partial": 12
  }
}
```

## Sample Adjudications

### cms2567_poc_04288d7fa777 / F0657 / adequate
- Facility: AVANTARA LAKE NORDEN
- Severity: B (low_severity)
- Primary vs audit: adequate /  (binary agree=None)
- Hidden correction metadata: Deficient, Provider has plan of correction / 2025-04-25
- Reason: The plan directly addresses the cited deficiency by updating the care plans for Resident 5 and the other impacted MCU residents to reflect actual call-light use abilities. It identifies the at-risk population, adds staff education, and includes a concrete audit and QAPI monitoring process with timing. This substantially responds to the deficient practice described.

**Deficiency excerpt**

> Based on observation, interview, record review, and policy review, the provider failed to ensure resident care plans were updated to accurately reflect the residents' abilities to use call lights effectively for five of five observed sampled residents (5, 18, 20, 21, and 23) with impaired cognition who resided in the memory care unit (MCU). Resident 5 sat on the edge of her bed and her call light was attached to the curtain in the center of the room between the two beds on the opposite side of the room from her bed on her roommate's side of the room on both days. Both call lights were on the same side of the room away from resident 5. She was unsure if there was a call light. She looked around and stated, "It wouldn't do me any good if I can't get to it." She said she would go to the dining room when she needed something. Review of resident 5's electronic medical record (EMR) revealed he

**Plan excerpt**

> The care plans were updated on March 19, 2025 for Resident 5 and the other residents in the Memory Care Unit to accurately reflect the resident's abilities to use call lights effectively with impaired cognition. Audits began on the main floor to ensure the care plan reflects the resident's abilities to use call lights effectively. All residents have a potential to be impacted by the care plan not accurately reflecting the residents' abilities to use call lights effectively with impaired cognition. Education was provided by Health Facilities Memory Care Unit Director, Director of Nursing and Administrator. Education to the Interdisciplinary Team was provided on March 20, 2025 by Memory Care Unit Director on the need for the care plans to accurately reflect the resident's abilities to use call lights effectively with impaired cognition. Director of Nursing (DNS) or designee conducted 100% 
### cms2567_poc_0570a70bbe77 / F0689 / inadequate
- Facility: Bethany Home - Brandon
- Severity: D (potential_harm)
- Primary vs audit: inadequate /  (binary agree=None)
- Hidden correction metadata: Deficient, Provider has date of correction / 2026-02-01
- Reason: The submitted plan of correction is not responsive to the deficiency narrative. The cited deficiencies concern an unsecured medication cart and substantiated abuse/neglect allegations, but the plan addresses respiratory care equipment, respiratory orders, and respiratory-care audits. Because it does not visibly correct the material cited practices, identify the affected population, or implement monitoring for the actual deficient practices, it is inadequate.

**Deficiency excerpt**

> Based on observation, interview, and policy review, the provider failed to ensure the medication cart was securely locked when the LPN walked away from it on 12/17/25. The medication cart should have been locked each time she walked away from it to ensure it was secured from unauthorized access. Review of the provider's 1/2025 Security of a Medication Cart policy revealed: 'The nurse/medication aide must secure the medication cart during the medication pass to prevent unauthorized entry.' 'Medication carts must be securely locked at all times when out of the nurse's/medication aide's view.' Continued from page 14 facility-reported incident (FRI), interview, record review, and policy review, the provider failed to protect three of three sampled residents (16, 37, and 50) and one of one closed sampled resident (101) from alleged verbal abuse and neglect. This citation is considered past no

**Plan excerpt**

> On 01/12/2026 the IDT, in collaboration with the facility medical director, reviewed and revised, as necessary, the policies and procedures relating to resident respiratory care. On 01/13/2026, the DON, or desginee, assessed the respiratory care devices of residents 8, 10, 49, and all residents to ensure their equipment was being stored appropriately. Resident 4 discharged from the facility on 01/09/2026. On 01/13/2026, the DON, or desginee, reviewed the respiratory care orders of residents 8, 10, 49, and all residents to ensure orders regarding respiratory care are accurate. Resident 4 discharged from the facility on 01/09/2026. Reviews will be completed by 01/16/2026. RNG, NLH, NL 1, DON B and all staff will be educated via in-service by 02/01/2026 regarding the policies and procedures related to resident respiratory care. Beginning 01/19/2026, DON, or designee, will audit respiratory 
### cms2567_poc_09dde23f0650 / F0812 / adequate
- Facility: GARDEN TERRACE HEALTHCARE CENTER OF FEDERAL WAY
- Severity: E (potential_harm)
- Primary vs audit: adequate /  (binary agree=None)
- Hidden correction metadata: Deficient, Provider has date of correction / 2025-08-04
- Reason: The plan directly responds to the cited unsafe kitchen sanitation conditions. It corrects the immediate sanitizer problem, addresses the dirty exhaust fans, adds staff education and a process for low-supply escalation, and establishes a concrete monitoring/QAPI follow-up structure with responsible parties and timeframes. While not highly detailed, it substantially covers the material deficiency narrative.

**Deficiency excerpt**

> Based on observation, interview, and record review the facility failed to prepare food under sanitary conditions for 1 of 1 facility kitchens. The failure to ensure cooking surface sanitizer was available at a suitable concentration and ensure exhaust fans were clean placed residents at risk for contaminated food and food-borne illness. According to the facility's 05/01/2025 Prevention of Cross Contamination policy, the facility must store, prepare, distribute and serve food in accordance with professional standards for food service safety. The policy showed all equipment, utensils, counters, workstations, and cutting boards should be cleaned and sanitized per department guidelines. Observation of the facility kitchen on 06/09/2025 at 8:40 AM (a Monday morning) showed the facility kitchen had two red buckets of surface sanitizer prepared. Testing of both buckets showed neither bucket had

**Plan excerpt**

> Sanitizer was acquired on 6/9/2025 and sanitizer mixed to the appropriate concentration. Exhaust fan vent/diffusers will be replaced. Education will be provided to dietary staff regarding the appropriate sanitizer concentration and the process for alerting the Dietary Manager when the supply of sanitizer is running low. Inspection of the vent cover/diffuser in the steam table area for cleanliness will be added to the monthly sanitation audit performed by either the dietary manager or the registered dietitian. ED/Designee will conduct audits 3 times per week for 8 weeks to verify that sanitizer is mixed to the appropriate concentration. ED/Designee will inspect the vent cover/diffuser in the steam table area to verify that they are free from dirt, dust and grime build up. Findings will be reported to QAPI Committee monthly x 3 months or until a lesser frequency is deemed appropriate. Exec
### cms2567_poc_0a2044fce15d / F0695 / partial
- Facility: SOUTH SHORE HEALTH & REHABILITATION CENTER
- Severity: D (potential_harm)
- Primary vs audit: partial /  (binary agree=None)
- Hidden correction metadata: Deficient, Provider has date of correction / 2024-08-21
- Reason: The plan responds to the two cited problems in a general way by auditing oxygen orders/flow rates and transportation for respiratory appointments, and it identifies the at-risk population. However, it is too vague to show how the facility will reliably prevent recurrence: it lacks a defined monitoring schedule, responsible staff, and any education or process change. It also does not clearly state the immediate correction for the resident's oxygen setting or the missed pulmonology appointment.

**Deficiency excerpt**

> Based on observation, record review, and interview, the facility failed to ensure oxygen was set at the correct flow rate and a resident was transported to the Pulmonologist's office for an appointment for 1 of 2 residents reviewed for respiratory care. (Resident C) During a phone interview on 7/19/24 at 11:20 a.m., Resident C's POA (power of attorney) indicated her mother had missed a cardio/pulmonologist appointment due to the facility not having transportation. The appointment was made over a year ago for the resident to be evaluated for a c-pap (continuous positive airway pressure) machine (a machine used that used mild air pressure to keep breathing airways open while sleeping). During random observations on 7/22/24 at 1:20 p.m., 3:30 p.m., and 4:48 p.m., the resident was observed wearing oxygen per nasal cannula at 0.75 liters per minute. The resident was connected to a portable ox

**Plan excerpt**

> Resident currently resides in the facility and has displayed no adverse effects, continues with normal daily routine. Audit of resident respiratory appointments to ensure transportation is scheduled to prevent missed appointments. Audit of resident supplemental oxygen order for flow rate accuracy and corresponding orders. All residents have the potential to be affected by this alleged deficiency. Audit of all resident's supplemental oxygen order for flow rate accuracy and corresponding orders. Audit of all resident respiratory appointments to ensure transportation is scheduled and secured to prevent missed appointments.
### cms2567_poc_0e27440c4bbe / F0550 / adequate
- Facility: SURRY COMMUNITY HEALTH CENTER BY HARBORVIEW
- Severity: G (actual_harm)
- Primary vs audit: adequate /  (binary agree=None)
- Hidden correction metadata: Deficient, Provider has date of correction / 2024-04-24
- Reason: The plan directly responds to the cited dignity failure by addressing the two affected residents, identifying the broader at-risk population of all incontinent residents, adding staff education on timely incontinence care and dignity, and establishing a concrete audit/QAPI monitoring process with a completion date. While not highly detailed, it substantially covers the main deficiency and systemic prevention elements.

**Deficiency excerpt**

> Based on record reviews, observations, resident, and staff interviews, the facility failed to protect residents' dignity when residents were left soiled in feces and saturated in urine for 2 of 2 residents reviewed for dignity issues (Resident #4 and Resident #305). When they were not provided incontinent care Resident #4 reported feeling unworthy of being looked at, sanitary rights being ignored, uncomfortable, and nasty; Resident #305 reported feeling cold, wet, and uncomfortable. Resident #4 was admitted to the facility on 6/22/23 with diagnoses including muscle weakness, neuromuscular dysfunction of the bladder, and the need for assistance with personal care. The Minimum Data Set (MDS) quarterly assessment dated 01/31/24 revealed Resident #4 was cognitively intact. She was incontinent of bowel, had an indwelling catheter, and required substantial maximum assistance by staff with toil

**Plan excerpt**

> 1. Immediate action(s) taken for the resident(s) found to have been affected include: Resident #4 on 3/17/24 at 2pm received incontinence care per the resident. Resident #305 on 3/17/24 at approximately 330pm had received incontinence care and was clean and dry per the resident. 2. Identification of other residents having the potential to be affected was accomplished by: The facility determined that all incontinent residents have potential to be affected. 3. Actions taken/systems put into place to reduce the risk of future occurrence include: The VP of Clinical, Regional Nurse, Administrator, Director of Nursing, Assistant DON, and/or Unit manager will provide education beginning 4/18/2024 to all staff on the Quality of Life-Dignity policy and the importance of ensuring that Dignity is maintained with regards to timely incontinence care. All new Staff will be in serviced on these items a
### cms2567_poc_0f6dd96c1cae / F0880 / inadequate
- Facility: DYER NURSING AND REHABILITATION CENTER
- Severity: E (potential_harm)
- Primary vs audit: inadequate /  (binary agree=None)
- Hidden correction metadata: Deficient, Provider has date of correction / 2023-01-06
- Reason: The plan only states that audits will be summarized to QA monthly and then quarterly. It does not describe any substantive corrective action addressing the cited infection control/linen deficiency, does not identify what will be audited, who will be corrected, or how the infection prevention system will be fixed. This is boilerplate monitoring language rather than a plan that responds to the deficiency narrative.

**Deficiency excerpt**

> The facility must establish and maintain an infection prevention and control program designed to provide a safe, sanitary and comfortable environment and to help prevent the development and transmission of communicable diseases and infections. §483.80(a) Infection prevention and control program. The facility must establish an infection prevention and control program (IPCP) that must include, at a minimum, the following elements: §483.80(a)(1) A system for preventing, identifying, reporting, investigating, and controlling infections and communicable diseases for all residents, staff, volunteers, visitors, and other individuals providing services under a contractual arrangement based upon the facility assessment conducted according to §483.70(e) and following accepted national standards; §483.80(a)(2) Written standards, policies, and procedures for the program, which must include, but are 

**Plan excerpt**

> Administrator/designee will present a summary of the audits to the Quality Assurance committee monthly for 6 months. Thereafter, if determined by the Quality Assurance committee, auditing and monitoring will be done quarterly and present quarterly at the QA meeting. Monitoring will be on going.
### cms2567_poc_103299bfa8ec / F0684 / inadequate
- Facility: FLEETWOOD POST-ACUTE
- Severity: J (immediate_jeopardy)
- Primary vs audit: inadequate /  (binary agree=None)
- Hidden correction metadata: Deficient, Provider has date of correction / 2023-10-20
- Reason: The plan of correction is only referenced by date and contains no actual corrective actions. It does not address the central deficiency: the wrong diet item being accessible to a resident with dysphagia and severe cognitive impairment, nor the delayed emergency response elements. There is no resident-specific remedy, no system change, no monitoring, and no implementation timeline visible in the plan text.

**Deficiency excerpt**

> A resident (R1) with Dementia and Parkinson's on a puree diet with thickened liquids aspirated on egg salad during supper on 09/18/2023. The resident grabbed an egg salad croissant sandwich from another resident's tray and took multiple bites before being given her meal tray which also contained egg salad sandwiches. CNA1 observed R1 eating while talking with a "mouth full of food" and instructed her to chew and slow down. Approximately 5 minutes later, R1 was found unresponsive by LPN1 at 5:45 PM in the dining room with egg salad noted on her face. The resident had a faint pulse, was unresponsive to verbal commands or physical touch, and her head was down. R1's pulse was lost at 5:54 PM. CPR was initiated and EMS was called. The Heimlich maneuver was not performed because R1 was already unresponsive. Finger sweeps were not done until R1 was wheeled to her room. The resident ultimately d

**Plan excerpt**

> Plan of Correction referenced at 10/20/23
### cms2567_poc_110d2b7cd053 / F0641 / partial
- Facility: CASCADES OF ST ANNE
- Severity: E (potential_harm)
- Primary vs audit: partial /  (binary agree=None)
- Hidden correction metadata: Deficient, Provider has date of correction / 2026-03-11
- Reason: The plan addresses the main cited inaccuracies by naming the affected residents, stating their MDSs were reviewed/corrected, and adding staff education plus ongoing audits/QAPI. However, it remains somewhat generic about how the facility will prevent recurrence of the specific documentation/coding failures (especially vaccine status and anticoagulant/GDR look-back validation), and it does not clearly define the exact process changes or completion timing for the corrective actions. That leaves a material gap in controlling the cited risk, so the response is meaningful but not fully adequate.

**Deficiency excerpt**

> Staff D stated that they did not see documentation that would support their MDS coding related to Resident 38's influenza vaccine status. Staff D further stated that it was an inaccurate MDS coding and that it would be modified. Review of Resident 36's face sheet printed on 01/20/2026 showed their birthdate of /1950. Review of Section O0300A in the annual MDS dated 01/02/2026 showed Resident 36's pneumococcal vaccination was coded as up to date. Review of Resident 36's immunization record showed they received their initial dose of pneumococcal vaccine [PPSV23] on 10/19/2004 when they were years old and another type of pneumococcal vaccine [PCV13] on 02/19/2019. Further review of the immunization record did not show Resident 36 received the recommended pneumococcal vaccine [PCV20 or PCV21] to be considered up to date per CDC guidelines. An interview and joint record review on 01/21/2026 a

**Plan excerpt**

> MDS assessments for Residents #7, #38, #36, #2, #3, and #19 were reviewed and corrected as needed to ensure accuracy related to Gradual Dose Reductions (GDRs), immunization status, and anticoagulant use. MDS assessments for residents admitted within the past 30 days were reviewed for accuracy and corrected as indicated. Education was provided to the Director of Nursing Services (DNS) and MDS Nurse on requirements for accurate MDS documentation, including Gradual Dose Reductions (GDRs), immunization status, and anticoagulant use. The Administrator or designee will conduct focused random audits to ensure MDS documentation related to GDRs, immunization status, and anticoagulant use is accurate weekly for four weeks, then monthly for two months. Results will be reviewed monthly for three months in QAPI. The Administrator or designee is responsible for ongoing compliance.
