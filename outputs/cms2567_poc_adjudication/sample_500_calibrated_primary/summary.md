# CMS-2567 POC Adjudication Pilot

This pilot adjudicates plan-of-correction adequacy from visible text only. The
adjudicators do not see correction status or correction date; those fields are
used only for later sanity checks.

## Setup

- Input: `outputs/cms2567_poc_adjudication/cms2567_poc_sample_500.jsonl`
- Primary model: `gpt-5.4-mini`
- Audit model: ``
- Rubric version: `calibrated`
- Rows: 500
- Estimated cost before run: 2.323341 USD

## Label Distribution

- Primary labels: {'partial': 318, 'adequate': 133, 'inadequate': 49}
- Audit labels: {}
- Primary binary labels: {'not_adequate': 367, 'adequate': 133}
- Binary primary/audit agreement: None
- Three-way primary/audit agreement: None
- Mean primary confidence: 0.9216
- Median days to correction by primary binary: {'adequate': 36, 'not_adequate': 36}

## By Severity Band

```json
{
  "actual_harm": {
    "partial": 63,
    "adequate": 9,
    "inadequate": 10
  },
  "immediate_jeopardy": {
    "partial": 43,
    "inadequate": 4,
    "adequate": 4
  },
  "low_severity": {
    "adequate": 23,
    "partial": 15,
    "inadequate": 4
  },
  "potential_harm": {
    "partial": 197,
    "adequate": 97,
    "inadequate": 31
  }
}
```

## By F-Tag Group

```json
{
  "abuse_neglect": {
    "partial": 51,
    "inadequate": 8,
    "adequate": 11
  },
  "care_planning_records": {
    "partial": 29,
    "adequate": 19,
    "inadequate": 4
  },
  "food_safety": {
    "partial": 26,
    "adequate": 22,
    "inadequate": 1
  },
  "infection_control": {
    "partial": 33,
    "inadequate": 5,
    "adequate": 12
  },
  "other": {
    "partial": 62,
    "adequate": 32,
    "inadequate": 9
  },
  "resident_care_safety": {
    "partial": 82,
    "inadequate": 16,
    "adequate": 13
  },
  "resident_rights": {
    "adequate": 24,
    "partial": 35,
    "inadequate": 6
  }
}
```

## Sample Adjudications

### cms2567_poc_003a4bca4196 / F0689 / partial
- Facility: WHITING GARDENS REHABILITATION AND NURSING CENTER
- Severity: J (immediate_jeopardy)
- Primary vs audit: partial /  (binary agree=None)
- Hidden correction metadata: Deficient, Provider has date of correction / 2025-05-02
- Reason: The plan meaningfully addresses the elopement-related systemic issues by revising the post-elopement protocol, educating staff, and adding audits/QAPI oversight. However, the deficiency narrative also cites missing documentation of frequent monitoring/care plan interventions and failure to complete the required social service assessment/follow-up after the incident. The plan does not clearly state how those specific resident-level omissions will be corrected or verified, so it is only partially responsive to the cited practice.

**Deficiency excerpt**

> Continued from page 11. Surveyor documented that the Unit Manager stated UMs are responsible for care planning and oversee care. CNAs were made aware of new interventions through daily assignments. In the presence of surveyor, the Unit Manager reviewed Resident #1's care plan intervention for frequent monitoring and stated it should be documented in the chart, noting CNAs would not document as it would be the nurse's responsibility. Review of electronic medical record did not reveal this documentation. CNA #3 on 3/7/25 at 6:16 P.M. did not recall seeing the resident during his shift. During interview on 3/8/2024 at 11:17 A.M., staff member stated she participated in incident response and would contact family if staff were unable. She was made aware of incident next day in morning meeting and team discussed how resident may have eloped, but she was unaware if identified. She was not asked

**Plan excerpt**

> An acceptable removal plan was electronically mailed to the surveyor on 3/10/25 at 9:31 A.M. indicating that the action the facility would take to prevent serious harm from occurring or recurring. The facility implemented a corrective action plan to remediate the deficient practice. Resident #1 has left the facility. All Elopement risk residents have the potential to be affected by this deficient practice. The facility implemented a revised Post Elopement Protocol to include checks of all egress doors, windows and wander guard functionality. The ADON/Designee had in-serviced the nursing staff and staff on the elopement drill process and the revised post elopement protocol. The ADON/Designee had in-serviced the staff on Incident protocol and Care Plan Policy. The ADON/Designee has already started weekly audits of all wander guards, egress doors, care plans and elopement investigations sin
### cms2567_poc_00c298dc4164 / F0812 / partial
- Facility: ABERDEEN HEALTH AND REHAB
- Severity: F (potential_harm)
- Primary vs audit: partial /  (binary agree=None)
- Hidden correction metadata: Deficient, Provider has date of correction / 2025-03-06
- Reason: The plan responds to the core issue by adding test strips, staff education, and an audit process, so it is not boilerplate. However, it remains materially incomplete because the deficiency was specifically about failure to monitor and record temperatures and sanitizer levels for the new chemical-sanitizing dishwasher, and the plan does not clearly establish the required log/documentation process or who will ensure ongoing entries at each meal/shift. The monitoring language is also vague and does not clearly define corrective action for abnormal readings or a firm completion basis.

**Deficiency excerpt**

> Review of the provider's 2013 Dish Machine Temperature Log policy revealed: 'Dishwashing staff will monitor and record dish machine temperatures to assure proper sanitizing of dishes.' 'The food service manager will provide the dishwashing staff with a log to be posted near the dish machine.' 'The food service manager will train dishwashing staff to monitor dish machine temperatures throughout the dishwashing process.' 'Staff will be trained to record dish machine temperatures for the wash and rinse cycles at each meal.' Interview on 2/6/25 at 12:18 p.m. with administrator A regarding the kitchen's mechanical dishwasher revealed she: Provided the mechanical dishwasher's manufacturer's manual and confirmed the new low temperature mechanical dishwasher that used chemical sanitization was put into service on 11/25/24. Agreed the 2013 Dish Machine Temperature Log policy was their current pol

**Plan excerpt**

> In continuing compliance with F0812, Food Procurement, Store/Prepare/Serve-Sanitary, Aberdeen Health & Rehab corrected the deficiency by ordering and receiving test strips beginning testing on 02/11/25. To correct the deficiency and to ensure the deficiency does not recur Dietary Staff were educated by Dietary Manager on dish machine chemical testing/temperature and recording process. Dietary Manager and/or designee will audit sanitizer testing 3x/week for 4 weeks, 2x/week for 4 weeks and 1x/week for 4 weeks then in randomly to ensure continue compliance. As part of Aberdeen Health & Rehabs ongoing commitment to quality assurance, the Executive Director and/or designee will report identified concerns through the community's QA Process.
### cms2567_poc_0114aa4ff4dd / F0838 / partial
- Facility: THE HSC PEDIATRIC SKILLED NURSING FACILITY
- Severity: D (potential_harm)
- Primary vs audit: partial /  (binary agree=None)
- Hidden correction metadata: Deficient, Provider has date of correction / 2024-10-18
- Reason: The plan acknowledges the deficiency and commits to completing the facility assessment and obtaining review, which is relevant. However, it is too vague on the core compliance problem: the survey found the assessment had not been completed annually and was not current. The plan does not clearly state how the overdue assessment will be brought up to date for the cited period, nor does it describe a concrete system change, monitoring process, or accountability step to ensure annual completion going forward. QAPI review alone is not enough without a defined audit or follow-up mechanism.

**Deficiency excerpt**

> Facility's Administrator failed to conduct and document a facility-wide assessment annually to determine what resources are necessary to care for its residents competently during the day-to-day operations (including nights and weekends) and emergencies. The facility's census on the first day of the survey was 14. Review of the facility's "SNF (skilled nursing facility)-Administrative - 009" policy last reviewed in January 2020, documented that a facility assessment is conducted annually to determine and update SNF's capacity to meet the needs of and completely care for residents during day-to-day operations and emergencies, with responsibility to the Administrator to lead this assessment with a multidisciplinary team. During the Recertification Survey conducted from 08/05/24 to 08/08/24, Employee #1 (Administrator) stated on 08/08/24 at 10:00 AM that the facility assessment was last comp

**Plan excerpt**

> The Administrator will provide the completed facility assessment to the COO and Quality Lead for review by the completions date of this POC. The Administrator will also ensure that the facility is completed within 45 days of the end of the calendar year. The facility assessment will be presented to the Quality Assurance and Performance Improvement Committee for review once completed and on an ongoing basis as warranted.
### cms2567_poc_027955a3300b / F0689 / partial
- Facility: Platte County Legacy Home
- Severity: G (actual_harm)
- Primary vs audit: partial /  (binary agree=None)
- Hidden correction metadata: Deficient, Provider has date of correction / 2026-04-01
- Reason: The plan contains meaningful systemic communication and monitoring steps, but it does not visibly address the central cited deficiency: failure to provide adequate supervision that resulted in harm to resident #10. It lacks resident-specific corrective action, does not describe how supervision will be increased for the affected or at-risk population, and does not tie the monitoring to concrete accident-prevention checks or outcomes. As written, it is more of a general process improvement than a direct correction of the cited deficient practice.

**Deficiency excerpt**

> Continued from page 11. Interview with the social services director on 2/20/26 at 9:27 AM confirmed there were no staff present who observed the incident and revealed there was no actual witnesses to the incident other than the residents, who had cognitive impairment. Based on medical record review, resident representative and staff interview, and facility incident review, the facility failed to ensure adequate supervision was provided to prevent resident injuries for 1 of 4 sample residents (#10) reviewed for accident hazards. The failure resulted in actual harm to resident #10. The findings were: (1) Review of the quarterly MDS assessment dated 2/2/26 showed resident #10 had short-term and long-term memory impairment and diagnoses which included non-Alzheimer's dementia. The MDS assessment showed the resident had physical and verbal behaviors directed towards others, other behavioral s

**Plan excerpt**

> Implement the "Stop and Watch" function in PointClickCare to enhance communication between nursing staff and management for staffing adjustments, supervision needs, and other pertinent information. Educate staff on proper use of the Stop and Watch tool. Implement standard operating procedure regarding Stop and Watch usage. Review Stop and Watch submissions during IDT Standup meetings, multiple times weekly. This will allow management to receive relevant information from staff multiple times per week, ensuring timely awareness of resident needs, trends, or risks and enabling proactive interventions to prevent accidents and monitor supervision needs.
### cms2567_poc_039fed207dd4 / F0804 / partial
- Facility: CHEROKEE COUNTY HEALTH AND REHABILITATION CENTER
- Severity: F (potential_harm)
- Primary vs audit: partial /  (binary agree=None)
- Hidden correction metadata: Deficient, Provider has date of correction / 2026-01-31
- Reason: The plan meaningfully responds to the deficiency by retraining staff on recipe adherence and temperature standards, identifying the meal-consuming population as potentially affected, and adding audits/QAPI follow-up. However, the cited problem was not just recipe deviation but food being served at unacceptable temperatures and unpalatable to specific residents, likely related to delivery/holding and seasoning/preparation issues. The plan does not clearly describe a concrete operational fix for maintaining hot/cold temperatures through service or a specific corrective action tied to the resident complaints, so it is only partially adequate.

**Deficiency excerpt**

> Based on observation, interview, record review, recipe review and facility policy review, the facility failed to serve food that was palatable and at an acceptable temperature to four of five residents (Resident (R) 5, R47, R144, and R139) reviewed for food palatability out of 36 sampled residents. This failure had the potential to affect 156 residents who consumed food prepared from the facility's kitchen and could result in residents skipping meals and experiencing weight loss. Review of R5's undated 'Admission Record,' located in the resident's electronic medical record (EMR) under the 'Profile' tab revealed R5 was admitted on 03/12/2025. Review of R5's quarterly 'Minimum Data Set (MDS)' with Assessment Reference Date (ARD) of 12/02/2025 and located in the resident's EMR under the 'MDS' tab revealed the facility assessed the resident to have a 'Brief Interview for Mental Score (BIMS)'

**Plan excerpt**

> 1. Immediate Correction: On 12/10/2025, the Dietary Manager provided re-education to dietary staff on strict adherence to approved facility recipes, including required ingredients, and that no additional seasonings or substitutions may be added unless approved by the Dietary Manager and/or Registered Dietitian. Food temperature standards were reviewed and reinforced with dietary staff. 2. Identification and Correction of Affected Residents: On 12/23/2025, all residents receiving meals prepared by the facility kitchen were identified as potentially affected. The Dietary Manager and/or designee monitored meal service and interviewed residents for concerns related to food temperature and palatability. Recent Resident Council meeting minutes were reviewed to ensure reported food concerns were addressed and resolved. Any concerns identified were addressed immediately. On 12/11/2025, the Dieta
### cms2567_poc_040a8cab5b8c / F0656 / partial
- Facility: CABELL HEALTHCARE CENTER
- Severity: D (potential_harm)
- Primary vs audit: partial /  (binary agree=None)
- Hidden correction metadata: Deficient, Provider has date of correction / 2024-03-09
- Reason: The plan does address the core cited practice of leaving medications at bedside through re-education, facility-wide education, and ongoing audits with QA reporting. However, it is weakened by the inclusion of unrelated activity care plan content, and it does not provide a clear resident-specific correction for the observed event or a concrete escalation/remediation process if audits find repeat noncompliance. Because the main deficiency is substantially addressed but the response is not fully focused or complete, it is partial rather than adequate.

**Deficiency excerpt**

> Based on observation, record review and staff interview, the facility failed to ensure the resident environment over which it had control was as free from accident hazards as possible. Medications were left at the bedside and lacked one half of a tablet of Zoloft. This was a random opportunity for discovery. Resident Identifier: #78. Facility Census: 88. On 02/14/24 at 10:05 AM it was observed that Resident #78 had a cup of medications at her bedside. Licensed Practical Nurse (LPN) #59 was called to the room. Upon further communication, it was determined that he had pulled the medications from the medication cart and was short one half (1/2) of a pill for the one of the ordered medications. The resident had been waiting for him to return to her room. The facility Policy and Procedure #NS-1197-05 Medication Administration states: "... Procedure: bb. Remain with the resident until the medi

**Plan excerpt**

> Licensed Practical Nurse #59 was given re-education on proper medication administration and not leaving medication bedside. (Attachment 689a) All residents that receive medication have the potential to be affected by this practice. On or before 03/04/2024 The Director of Nurses and/or designee completed educations with all Unit Charge Nurses on proper medication administration and safe practices and not leaving a resident medication at bedside. (Attachment 689b) The Unit Manager will complete daily (5 days per week) audits of medication pass to assure medication are being administered per policy and no medications are being left at bedside. The Unit Manager will report results to the Quality Assurance Committee monthly to ensure continued compliance. 1. On 02/14/2024 the Activity Director edited Resident #37 care plan to remove the language 'Provide 1:1 in room visits if unable to attend
### cms2567_poc_04288d7fa777 / F0657 / adequate
- Facility: AVANTARA LAKE NORDEN
- Severity: B (low_severity)
- Primary vs audit: adequate /  (binary agree=None)
- Hidden correction metadata: Deficient, Provider has plan of correction / 2025-04-25
- Reason: The plan directly addresses the cited deficiency by updating the care plans for Resident 5 and the other impacted memory care residents so they accurately reflect call-light use abilities. It identifies the at-risk population, provides staff education, establishes ongoing audits with a defined schedule, and includes QAPI follow-up and a completion basis. While it does not spell out every operational detail, it substantially responds to the material deficiency narrative.

**Deficiency excerpt**

> Based on observation, interview, record review, and policy review, the provider failed to ensure resident care plans were updated to accurately reflect the residents' abilities to use call lights effectively for five of five observed sampled residents (5, 18, 20, 21, and 23) with impaired cognition who resided in the memory care unit (MCU). Resident 5 sat on the edge of her bed and her call light was attached to the curtain in the center of the room between the two beds on the opposite side of the room from her bed on her roommate's side of the room on both days. Both call lights were on the same side of the room away from resident 5. She was unsure if there was a call light. She looked around and stated, "It wouldn't do me any good if I can't get to it." She said she would go to the dining room when she needed something. Review of resident 5's electronic medical record (EMR) revealed he

**Plan excerpt**

> The care plans were updated on March 19, 2025 for Resident 5 and the other residents in the Memory Care Unit to accurately reflect the resident's abilities to use call lights effectively with impaired cognition. Audits began on the main floor to ensure the care plan reflects the resident's abilities to use call lights effectively. All residents have a potential to be impacted by the care plan not accurately reflecting the residents' abilities to use call lights effectively with impaired cognition. Education was provided by Health Facilities Memory Care Unit Director, Director of Nursing and Administrator. Education to the Interdisciplinary Team was provided on March 20, 2025 by Memory Care Unit Director on the need for the care plans to accurately reflect the resident's abilities to use call lights effectively with impaired cognition. Director of Nursing (DNS) or designee conducted 100% 
### cms2567_poc_051aa5dc39a1 / F0880 / partial
- Facility: JUDSON PARK HEALTH CENTER
- Severity: D (potential_harm)
- Primary vs audit: partial /  (binary agree=None)
- Hidden correction metadata: Deficient, Provider has date of correction / 2025-10-21
- Reason: The plan includes relevant infection-control education, some auditing, and QAPI follow-up, which are meaningful corrective components. However, it is too generic relative to the cited deficiency narrative. The main problem was staff failing to use PPE and perform hand hygiene correctly during care for residents on EBP/contact enteric precautions. The plan does not clearly specify targeted correction of those exact practice failures, does not describe direct observation of staff compliance with the required donning/doffing and soap-and-water hand hygiene steps, and does not include a concrete escalation or accountability process if noncompliance is found. It therefore only partially addresses the material deficiency.

**Deficiency excerpt**

> Staff M was observed to clean Resident 27 after changing their soiled incontinent pad. Staff M did not remove soiled gloves or wash hands before putting on moisturizing ointment on Resident 27's skin or before helping Resident 27 look through their drawers for their glasses or when using the bed remote to lower their bed. Resident 27 stated they had ongoing diarrhea and were being fed through a tube. According to the 07/23/2025 quarterly MDS, Resident 6 had a neurological condition, required a feeding tube to eat, and used an indwelling catheter (tube inserted in the urinary tract from the bladder) due to urinary blockage. Review of the 08/09/2024, MRSA (Methicillin-Resistant Staphylococcus Aurea) CP, Resident 6 was on EBP due to their feeding tube and a history of multiple drug-resistant organisms that were resistant to multiple antibiotics for treatments. Observation on 08/25/2025 at 8

**Plan excerpt**

> Staff have been educated on different types of transmission based precautions. Auditing of staff on transmission based precautions will completed 3 times weekly for 1 month and then weekly for 2 months. How the facility plans to monitor its performance to make sure that solutions are sustained: Education records and auditing tools will be forwarded to QAPI (Quality Assurance/ Performance Improvement) for validation of ongoing compliance for 3 months reviewing for further educational opportunities, review trends and further system review. F-880 Infection Control Program Enhanced Barrier Precautions (D). How the facility will correct the deficiency as relates to the resident(s): Resident #37 no longer resides at the facility. Resident #54 bed remote and door handle have been disinfected. Resident #2 has received a new wheelchair. Resident #27 drawers, glasses and t.v. remote have been disi
