# CMS-2567 POC Adjudication Pilot

This pilot adjudicates plan-of-correction adequacy from visible text only. The
adjudicators do not see correction status or correction date; those fields are
used only for later sanity checks.

## Setup

- Input: `outputs/cms2567_poc_adjudication/calibrated_audit_balanced_50_input.jsonl`
- Primary model: `gpt-4o-mini`
- Audit model: ``
- Rubric version: `calibrated`
- Rows: 50
- Estimated cost before run: 0.036732 USD

## Label Distribution

- Primary labels: {'adequate': 33, 'inadequate': 7, 'partial': 10}
- Audit labels: {}
- Primary binary labels: {'adequate': 33, 'not_adequate': 17}
- Binary primary/audit agreement: None
- Three-way primary/audit agreement: None
- Mean primary confidence: 0.838
- Median days to correction by primary binary: {'adequate': 36, 'not_adequate': 44}

## By Severity Band

```json
{
  "actual_harm": {
    "partial": 5,
    "adequate": 6,
    "inadequate": 1
  },
  "immediate_jeopardy": {
    "inadequate": 2,
    "partial": 4,
    "adequate": 6
  },
  "low_severity": {
    "adequate": 6,
    "partial": 1,
    "inadequate": 1
  },
  "potential_harm": {
    "inadequate": 3,
    "adequate": 15
  }
}
```

## By F-Tag Group

```json
{
  "abuse_neglect": {
    "partial": 2,
    "inadequate": 1,
    "adequate": 2
  },
  "care_planning_records": {
    "adequate": 4
  },
  "food_safety": {
    "adequate": 3
  },
  "infection_control": {
    "inadequate": 2,
    "adequate": 3
  },
  "other": {
    "adequate": 11,
    "partial": 3,
    "inadequate": 1
  },
  "resident_care_safety": {
    "inadequate": 3,
    "partial": 3,
    "adequate": 3
  },
  "resident_rights": {
    "adequate": 7,
    "partial": 2
  }
}
```

## Sample Adjudications

### cms2567_poc_04288d7fa777 / F0657 / adequate
- Facility: AVANTARA LAKE NORDEN
- Severity: B (low_severity)
- Primary vs audit: adequate /  (binary agree=None)
- Hidden correction metadata: Deficient, Provider has plan of correction / 2025-04-25
- Reason: The plan addresses the main resident-specific correction, includes education for staff, outlines a monitoring process, and specifies a timeline for audits.

**Deficiency excerpt**

> Based on observation, interview, record review, and policy review, the provider failed to ensure resident care plans were updated to accurately reflect the residents' abilities to use call lights effectively for five of five observed sampled residents (5, 18, 20, 21, and 23) with impaired cognition who resided in the memory care unit (MCU). Resident 5 sat on the edge of her bed and her call light was attached to the curtain in the center of the room between the two beds on the opposite side of the room from her bed on her roommate's side of the room on both days. Both call lights were on the same side of the room away from resident 5. She was unsure if there was a call light. She looked around and stated, "It wouldn't do me any good if I can't get to it." She said she would go to the dining room when she needed something. Review of resident 5's electronic medical record (EMR) revealed he

**Plan excerpt**

> The care plans were updated on March 19, 2025 for Resident 5 and the other residents in the Memory Care Unit to accurately reflect the resident's abilities to use call lights effectively with impaired cognition. Audits began on the main floor to ensure the care plan reflects the resident's abilities to use call lights effectively. All residents have a potential to be impacted by the care plan not accurately reflecting the residents' abilities to use call lights effectively with impaired cognition. Education was provided by Health Facilities Memory Care Unit Director, Director of Nursing and Administrator. Education to the Interdisciplinary Team was provided on March 20, 2025 by Memory Care Unit Director on the need for the care plans to accurately reflect the resident's abilities to use call lights effectively with impaired cognition. Director of Nursing (DNS) or designee conducted 100% 
### cms2567_poc_0570a70bbe77 / F0689 / inadequate
- Facility: Bethany Home - Brandon
- Severity: D (potential_harm)
- Primary vs audit: inadequate /  (binary agree=None)
- Hidden correction metadata: Deficient, Provider has date of correction / 2026-02-01
- Reason: The plan does not address the specific deficiencies related to the unsecured medication cart or the verbal abuse and neglect of residents. It focuses on respiratory care, which is unrelated to the cited deficiencies.

**Deficiency excerpt**

> Based on observation, interview, and policy review, the provider failed to ensure the medication cart was securely locked when the LPN walked away from it on 12/17/25. The medication cart should have been locked each time she walked away from it to ensure it was secured from unauthorized access. Review of the provider's 1/2025 Security of a Medication Cart policy revealed: 'The nurse/medication aide must secure the medication cart during the medication pass to prevent unauthorized entry.' 'Medication carts must be securely locked at all times when out of the nurse's/medication aide's view.' Continued from page 14 facility-reported incident (FRI), interview, record review, and policy review, the provider failed to protect three of three sampled residents (16, 37, and 50) and one of one closed sampled resident (101) from alleged verbal abuse and neglect. This citation is considered past no

**Plan excerpt**

> On 01/12/2026 the IDT, in collaboration with the facility medical director, reviewed and revised, as necessary, the policies and procedures relating to resident respiratory care. On 01/13/2026, the DON, or desginee, assessed the respiratory care devices of residents 8, 10, 49, and all residents to ensure their equipment was being stored appropriately. Resident 4 discharged from the facility on 01/09/2026. On 01/13/2026, the DON, or desginee, reviewed the respiratory care orders of residents 8, 10, 49, and all residents to ensure orders regarding respiratory care are accurate. Resident 4 discharged from the facility on 01/09/2026. Reviews will be completed by 01/16/2026. RNG, NLH, NL 1, DON B and all staff will be educated via in-service by 02/01/2026 regarding the policies and procedures related to resident respiratory care. Beginning 01/19/2026, DON, or designee, will audit respiratory 
### cms2567_poc_09dde23f0650 / F0812 / adequate
- Facility: GARDEN TERRACE HEALTHCARE CENTER OF FEDERAL WAY
- Severity: E (potential_harm)
- Primary vs audit: adequate /  (binary agree=None)
- Hidden correction metadata: Deficient, Provider has date of correction / 2025-08-04
- Reason: The plan addresses the main issues of sanitizer concentration and exhaust fan cleanliness, includes education and monitoring, and assigns responsibility for compliance.

**Deficiency excerpt**

> Based on observation, interview, and record review the facility failed to prepare food under sanitary conditions for 1 of 1 facility kitchens. The failure to ensure cooking surface sanitizer was available at a suitable concentration and ensure exhaust fans were clean placed residents at risk for contaminated food and food-borne illness. According to the facility's 05/01/2025 Prevention of Cross Contamination policy, the facility must store, prepare, distribute and serve food in accordance with professional standards for food service safety. The policy showed all equipment, utensils, counters, workstations, and cutting boards should be cleaned and sanitized per department guidelines. Observation of the facility kitchen on 06/09/2025 at 8:40 AM (a Monday morning) showed the facility kitchen had two red buckets of surface sanitizer prepared. Testing of both buckets showed neither bucket had

**Plan excerpt**

> Sanitizer was acquired on 6/9/2025 and sanitizer mixed to the appropriate concentration. Exhaust fan vent/diffusers will be replaced. Education will be provided to dietary staff regarding the appropriate sanitizer concentration and the process for alerting the Dietary Manager when the supply of sanitizer is running low. Inspection of the vent cover/diffuser in the steam table area for cleanliness will be added to the monthly sanitation audit performed by either the dietary manager or the registered dietitian. ED/Designee will conduct audits 3 times per week for 8 weeks to verify that sanitizer is mixed to the appropriate concentration. ED/Designee will inspect the vent cover/diffuser in the steam table area to verify that they are free from dirt, dust and grime build up. Findings will be reported to QAPI Committee monthly x 3 months or until a lesser frequency is deemed appropriate. Exec
### cms2567_poc_0f6dd96c1cae / F0880 / inadequate
- Facility: DYER NURSING AND REHABILITATION CENTER
- Severity: E (potential_harm)
- Primary vs audit: inadequate /  (binary agree=None)
- Hidden correction metadata: Deficient, Provider has date of correction / 2023-01-06
- Reason: The plan does not address the specific components required for an infection prevention and control program as outlined in the deficiency narrative.

**Deficiency excerpt**

> The facility must establish and maintain an infection prevention and control program designed to provide a safe, sanitary and comfortable environment and to help prevent the development and transmission of communicable diseases and infections. §483.80(a) Infection prevention and control program. The facility must establish an infection prevention and control program (IPCP) that must include, at a minimum, the following elements: §483.80(a)(1) A system for preventing, identifying, reporting, investigating, and controlling infections and communicable diseases for all residents, staff, volunteers, visitors, and other individuals providing services under a contractual arrangement based upon the facility assessment conducted according to §483.70(e) and following accepted national standards; §483.80(a)(2) Written standards, policies, and procedures for the program, which must include, but are 

**Plan excerpt**

> Administrator/designee will present a summary of the audits to the Quality Assurance committee monthly for 6 months. Thereafter, if determined by the Quality Assurance committee, auditing and monitoring will be done quarterly and present quarterly at the QA meeting. Monitoring will be on going.
### cms2567_poc_103299bfa8ec / F0684 / inadequate
- Facility: FLEETWOOD POST-ACUTE
- Severity: J (immediate_jeopardy)
- Primary vs audit: inadequate /  (binary agree=None)
- Hidden correction metadata: Deficient, Provider has date of correction / 2023-10-20
- Reason: The plan of correction does not provide any specific actions or systemic changes to address the cited deficiency regarding R1's care and the failure to adhere to her dietary needs, nor does it include any monitoring or follow-up mechanisms.

**Deficiency excerpt**

> A resident (R1) with Dementia and Parkinson's on a puree diet with thickened liquids aspirated on egg salad during supper on 09/18/2023. The resident grabbed an egg salad croissant sandwich from another resident's tray and took multiple bites before being given her meal tray which also contained egg salad sandwiches. CNA1 observed R1 eating while talking with a "mouth full of food" and instructed her to chew and slow down. Approximately 5 minutes later, R1 was found unresponsive by LPN1 at 5:45 PM in the dining room with egg salad noted on her face. The resident had a faint pulse, was unresponsive to verbal commands or physical touch, and her head was down. R1's pulse was lost at 5:54 PM. CPR was initiated and EMS was called. The Heimlich maneuver was not performed because R1 was already unresponsive. Finger sweeps were not done until R1 was wheeled to her room. The resident ultimately d

**Plan excerpt**

> Plan of Correction referenced at 10/20/23
### cms2567_poc_176f28ecede7 / F0697 / partial
- Facility: SURRY COMMUNITY HEALTH CENTER BY HARBORVIEW
- Severity: K (immediate_jeopardy)
- Primary vs audit: partial /  (binary agree=None)
- Hidden correction metadata: Deficient, Provider has date of correction / 2024-04-24
- Reason: The plan addresses the potential for other residents to be affected and mentions actions taken, but it lacks specific corrective actions for Resident #21's pain management, monitoring mechanisms, and does not detail how the facility will prevent future occurrences related to medication administration issues.

**Deficiency excerpt**

> Based on observation, record review and resident, resident representative, Pharmacy, Medical Director (MD), Physician Assistant (PA), and staff interviews, the facility failed to address a resident's pain (Resident #21) after repeated reports to staff that she had not received her pain medications during the night shift (7:00 AM to 7:00 PM). Resident #21 reported starting the end of November 2023 she was told by Medication Aide (MA) #3 the facility had run out of her Methadone (analgesic opioid agonist), or MA #3 would tell her that she would bring her pain medication and never return during the night shift. Resident #21 informed the PA on 12/12/23 that her pain medications were not being given to her. On 1/05/24 Resident #21 was seen by the PA and reported increased pain primarily at night. Resident #21 reported when she was not administered her Methadone, she experienced terrible/awful

**Plan excerpt**

> Resident #21's Medical Doctor (MD) was called on 3/21/24 and stated that it was unsafe to give her anymore pain medications at this time. The MD agreed and the resident agreed to be evaluated at a pain clinic. The resident visited the Bethany Pain Clinic on 4/9/24. The provider at the clinic would not see or adjust the resident's medication because of how high the residents dosage is already. The resident was interviewed by the DON on 4/22/24 again about seeing another pain clinic or doctor about her pain and she says that she does not want to go anywhere else at this time. Identification of other residents having the potential to be affected was accomplished by: The facility has determined that all residents have the potential to be affected. Actions taken/systems put into place to reduce the risk of future occurrence include: The DON, ADON and/or Regional Nurse
### cms2567_poc_1de32a6f28dc / F0600 / partial
- Facility: SCOTCHMAN LIVING CENTER
- Severity: G (actual_harm)
- Primary vs audit: partial /  (binary agree=None)
- Hidden correction metadata: Past Non-Compliance / 2024-02-28
- Reason: The plan addresses staff reeducation and systemic actions but lacks specific details on monitoring and follow-up mechanisms, as well as a concrete timeline for completion.

**Deficiency excerpt**

> Based on observation, record review, interview, and policy review during survey 12/17/24, 12/18/24, and 12/19/24, random interviews with residents revealed no other residents voiced concerns regarding potential neglect. Observations and interviews with nursing staff revealed appropriate resident transfers according to residents' care plans. Review of staff training records revealed staff were educated about accident prevention and re-educated about following residents' care plans on 2/26/24 and 2/28/24. Non-compliance at F600 occurred on 2/23/24.

**Plan excerpt**

> DON reeducated all staff at the monthly staff meeting in February 2024. Those staff who were not in attendance were reeducated prior to their next working shift on accident hazards and following residents' care plans. The provider's implemented systemic actions to ensure the deficient practice does not reoccur was confirmed on 12/19/24 after record review revealed the facility had followed their quality assurance process, education was provided to all staff about accident prevention and following resident care plans, and observations and interviews revealed staff understood the education provided regarding those topics. Past noncompliance: no plan of correction required.
### cms2567_poc_287470b6f2d5 / F0698 / adequate
- Facility: WONDER CITY REHABILITATION AND NURSING CENTER
- Severity: G (actual_harm)
- Primary vs audit: adequate /  (binary agree=None)
- Hidden correction metadata: Deficient, Provider has date of correction / 2023-10-09
- Reason: The plan addresses the main issues related to R7's meal provision and includes education, monitoring, and follow-up mechanisms.

**Deficiency excerpt**

> An additional interview with R7 on 07/10/23 at 6:07 AM revealed she was leaving her room to go for her dialysis treatment and had not received her breakfast meal. Observation on 07/10/23 at 6:17 AM revealed R7 was seated in her wheelchair near the nurse's station when a nurse offered her a Styrofoam container. R7 was observed to look inside the container and stated that she could not eat any of the food and left the container at the nurse's station. Interview with R7 on 07/10/23 at 6:18 AM revealed the items in the Styrofoam container were all too sweet and would "run her sugar up," so she could not eat any of it. Observation of the contents of the Styrofoam container revealed it contained a carton of whole milk, raisin bran cereal, yogurt, fruit punch, apple sauce, and a banana. Observation on 07/10/23 at 6:22 AM revealed a nurse provided R7 with her "dialysis bag." R7 was observed to l

**Plan excerpt**

> 1. Resident #7 is receiving a bagged meal with preferred foods and foods within the ordered diet to take with her to dialysis treatments. 2. Residents receiving dialysis treatments are at risk. 3. The SDC/designee will educate all nurses and CNAs on ensuring provision of bagged meal for Residents going to outside dialysis treatment. The Dietary Department will be educated by the SDC/designee on ensuring availability of bagged meals per Resident preference and according to the ordered diet for Residents going to outside dialysis treatment. 4. The UM/designee will audit Residents going to outside dialysis treatments weekly times 4 to ensure that a bagged meal with preferred foods and foods per the ordered diet was provided. Results of the audits will be reviewed at the QA meeting on a monthly basis times 2.
