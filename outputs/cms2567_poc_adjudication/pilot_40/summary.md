# CMS-2567 POC Adjudication Pilot

This pilot adjudicates plan-of-correction adequacy from visible text only. The
adjudicators do not see correction status or correction date; those fields are
used only for later sanity checks.

## Setup

- Input: `outputs/cms2567_poc_adjudication/cms2567_poc_pilot_40.jsonl`
- Primary model: `gpt-5.4-mini`
- Audit model: `gpt-4o-mini`
- Rows: 40
- Estimated cost before run: 0.219190 USD

## Label Distribution

- Primary labels: {'partial': 35, 'inadequate': 4, 'adequate': 1}
- Audit labels: {'adequate': 6, 'partial': 31, 'inadequate': 3}
- Primary binary labels: {'not_adequate': 39, 'adequate': 1}
- Binary primary/audit agreement: 0.875
- Three-way primary/audit agreement: 0.8
- Mean primary confidence: 0.917
- Median days to correction by primary binary: {'adequate': 44, 'not_adequate': 38}

## By Severity Band

```json
{
  "actual_harm": {
    "inadequate": 1,
    "partial": 6
  },
  "immediate_jeopardy": {
    "partial": 10,
    "inadequate": 1
  },
  "low_severity": {
    "partial": 2,
    "inadequate": 1
  },
  "potential_harm": {
    "partial": 17,
    "inadequate": 1,
    "adequate": 1
  }
}
```

## By F-Tag Group

```json
{
  "abuse_neglect": {
    "inadequate": 1,
    "partial": 6
  },
  "care_planning_records": {
    "partial": 4
  },
  "food_safety": {
    "partial": 2
  },
  "infection_control": {
    "partial": 1
  },
  "other": {
    "partial": 11,
    "inadequate": 3
  },
  "resident_care_safety": {
    "partial": 8
  },
  "resident_rights": {
    "partial": 3,
    "adequate": 1
  }
}
```

## Sample Adjudications

### cms2567_poc_1b9cefc419a0 / F0656 / partial
- Facility: HILLSIDE NURSING AND REHABILITATION CENTER
- Severity: J (immediate_jeopardy)
- Primary vs audit: partial / adequate (binary agree=False)
- Hidden correction metadata: Deficient, Provider has date of correction / 2024-04-28
- Reason: The plan addresses the main elopement event and adds care plans/training/audits, which is responsive. However, it does not fully and specifically correct every cited deficiency: it omits a concrete fix for the Wanderguard check failure that contributed to the elopement, and it does not clearly resolve the Resident #52 activity-preference care plan issue. The monitoring is present but broad, and the plan is only partially tailored to the cited breakdowns.

**Deficiency excerpt**

> CFR(s): 483.21(b)(4)(3) §483.21(b) Comprehensive Care Plans §483.21(b)(1) The facility must develop and Continued from page 12. Facility failed to ensure proper supervision and monitoring of residents with elopement risk. Resident #13 had a Wanderguard bracelet as part of care plan, but nightshift staff failed to check the function and placement of the bracelet. ADON stated Resident #13 never gave indication she would elope, so care plan was not updated with increased supervision interventions. DON stated there was no logical explanation for staff not following resident's care plan to check Wanderguard bracelet placement and function. Administrator expected residents' care plans to be updated and interventions followed according to facility policy. Facility also failed to develop comprehensive care plans for Resident #40 admitted 12/15/2023 with spina bifida, carpal tunnel syndrome bilat

**Plan excerpt**

> On 3/14/2024, the Minimum Data Set Coordinator (MDS) created an intervention for increased monitoring related to resident #13 presenting with exit-seeking behavior. On 4/08/24, Minimum Data Set Coordinator (MDS) reviewed resident #13's care plan to verify elopement interventions were in place. All were implemented as directed in the care plan. On 3/14/24, the Licensed Nurse (LN) assessed Resident #13 once back in building. No injuries noted. On 3/14/24, the LN applied a wander guard to Resident #13's left ankle. On 3/14/2024, the Director of Nursing (DON) initiated 1:1 for Resident #13. On 3/15/24, the Maintenance Director and Regional Director of Plant Operations repaired the 400-wing door with wander guard alarm system. On 4/24/2024, the Director of Nursing (DON) created a care plan for pain related to carpal tunnel diagnosis for resident #40. On 4/24/2024, the DON created a care plan 
### cms2567_poc_22c44bedd173 / F0686 / partial
- Facility: HAVEN OF SANDPOINTE, LLC
- Severity: E (potential_harm)
- Primary vs audit: partial / partial (binary agree=True)
- Hidden correction metadata: Deficient, Provider has date of correction / 2022-09-18
- Reason: The plan goes beyond boilerplate by naming at-risk residents, adding education, and setting up audits with responsibility and QAPI follow-up. However, it only partially addresses the core deficiency. The cited problem included failure to obtain/implement a pressure-relieving boots order and missed/undocumented wound treatments for resident #69, but the plan does not clearly state immediate correction of those specific omissions or a system change to ensure wound orders are entered and treatments are actually provided on schedule. The monitoring is helpful but not tightly linked to the exact breakdowns described in the narrative.

**Deficiency excerpt**

> Continued from page 12. Review of medical records revealed a resident with a sacral wound initially described as MASO/shear measuring 4.2 cm x 0.9 cm x 0.1 cm with serous drainage, 26-50% epithelialization, 1-25% slough, and 1-25% pink granulation. Wound orders included cleansing with NS, applying medical grade honey, and dry protective dressing daily. Treatments were administered per orders from 07/06 through 07/11. Physician progress note dated 07/12/22 at 4:06 p.m. revealed the wound measured 2.2 cm x 0.7 cm with serous drainage, 1-25% epithelialization, and 51-75% slough, and the note stated the wound was deteriorating. Orders included cleansing with NS, applying medical grade honey, dry protective dressing daily, and repositioning per facility protocol. However, the repositioning order was not added to the July 2022 TAR until 07/14/22. No evidence provided indicating whether treatme

**Plan excerpt**

> The facility has determined that all residents with a pressure injury are at risk to be affected by this deficiency. Residents #12 and #291 no longer reside in facility. Complete review of Resident #69 clinical record. Wound Nurse Practitioner assessed wound to left heel on 08/23/22. Plan of care reviewed and revised as needed to reflect residents' current status. All licensed staff and certified staff to receive Pressure Ulcer Prevention education on 09/06/2022. All licensed staff to receive education regarding Pressure Ulcer Care and Treatment 09/06/2022. Director of Nursing or designee will complete audit on all new admissions skin assessments x 30 days to promote healing, prevent infection and prevent new ulcers from developing. Audit will then continue with 10 residents monthly. DON or designee will complete audit on all residents with a pressure ulcer every week x 4 weeks to ensure
### cms2567_poc_2385c0cbf3fd / F0760 / inadequate
- Facility: EVERGREEN POST ACUTE
- Severity: G (actual_harm)
- Primary vs audit: inadequate / partial (binary agree=True)
- Hidden correction metadata: Past Non-Compliance / 2024-09-18
- Reason: The plan addresses the individual staff member after the fact, but it does not adequately respond to the cited deficiency that the facility failed to ensure the resident was free from a medication error causing hypotension and hospital transfer. It lacks resident-centered immediate actions, broader risk assessment for other residents, and systemic fixes to the medication administration process (e.g., identification checks, MAR/photo verification, competency validation for all med-pass staff). The statement 'Past noncompliance: no plan of correction required' is also not a corrective plan and leaves the cited deficiency materially unaddressed.

**Deficiency excerpt**

> 4/11/25 3:12 PM - A review of the facility's incident investigation provided a typed and signed statement from E27 (staff LPN) stating,"Around 8:15 AM, I pulled R644 roommate's medications. I was looking at the name in the room, there was only one name in there. I took her blood pressure, and it was normal. I called her [R644's roommate's name]. I said to R644, 'I have your medication' and she said I need my medication in pudding. I did not know she [R644] was hard of hearing. I gave medication and then I went to the roommate in B bed and that's when I realized I gave A bed, B bed's medication. I looked at the arm bands after I realized I made a mistake. At 8:20 AM the unit manager contacted the provider and provider stated to recheck the vital signs in an hour. I re-checked her in about an hour later. Her blood pressure was 74/55 automatic blood pressure machine and then re-checked agai

**Plan excerpt**

> Timely reporting to the state Agency; Additional education regarding medication administration for E27; Additional monitoring of E27 including a "3-person med pass" with the Pharmacist to verify her knowledge of med administration and shadowing during all med passes until she was cleared for normal duty. E27 was terminated on 1/1/25 for failing to perform the requirements of the job. Notification of the family informing them of the medication error. Past noncompliance: no plan of correction required.
### cms2567_poc_287470b6f2d5 / F0698 / partial
- Facility: WONDER CITY REHABILITATION AND NURSING CENTER
- Severity: G (actual_harm)
- Primary vs audit: partial / partial (binary agree=True)
- Hidden correction metadata: Deficient, Provider has date of correction / 2023-10-09
- Reason: The plan responds to the core dialysis-bag issue by providing R7 a bagged meal with preferred and renal-diet foods, identifies dialysis residents as at risk, and includes staff education plus audit/QA monitoring. However, the deficiency also cites that R7 was not consistently served breakfast before leaving for 6:30 AM dialysis, and the plan does not clearly correct the timing/coordination failure between dietary and nursing to ensure breakfast is actually delivered before transport. It focuses mainly on the contents of the dialysis bag, leaving a meaningful gap in the cited deficient practice.

**Deficiency excerpt**

> An additional interview with R7 on 07/10/23 at 6:07 AM revealed she was leaving her room to go for her dialysis treatment and had not received her breakfast meal. Observation on 07/10/23 at 6:17 AM revealed R7 was seated in her wheelchair near the nurse's station when a nurse offered her a Styrofoam container. R7 was observed to look inside the container and stated that she could not eat any of the food and left the container at the nurse's station. Interview with R7 on 07/10/23 at 6:18 AM revealed the items in the Styrofoam container were all too sweet and would "run her sugar up," so she could not eat any of it. Observation of the contents of the Styrofoam container revealed it contained a carton of whole milk, raisin bran cereal, yogurt, fruit punch, apple sauce, and a banana. Observation on 07/10/23 at 6:22 AM revealed a nurse provided R7 with her "dialysis bag." R7 was observed to l

**Plan excerpt**

> 1. Resident #7 is receiving a bagged meal with preferred foods and foods within the ordered diet to take with her to dialysis treatments. 2. Residents receiving dialysis treatments are at risk. 3. The SDC/designee will educate all nurses and CNAs on ensuring provision of bagged meal for Residents going to outside dialysis treatment. The Dietary Department will be educated by the SDC/designee on ensuring availability of bagged meals per Resident preference and according to the ordered diet for Residents going to outside dialysis treatment. 4. The UM/designee will audit Residents going to outside dialysis treatments weekly times 4 to ensure that a bagged meal with preferred foods and foods per the ordered diet was provided. Results of the audits will be reviewed at the QA meeting on a monthly basis times 2.
### cms2567_poc_29433b15f725 / F0684 / partial
- Facility: DELAWARE VETERANS HOME
- Severity: G (actual_harm)
- Primary vs audit: partial / partial (binary agree=True)
- Hidden correction metadata: Deficient, Provider has date of correction / 2025-04-30
- Reason: The plan meaningfully responds to the lab-result/UTI delay portion of the deficiency by identifying a root cause, changing the lab/EMR process, educating staff, and adding monitoring. However, the cited deficiency also includes failure to follow physician orders for R35 and R41, and the plan does not provide any resident-specific correction, system fix, or monitoring for medication parameter compliance. Because it only partially addresses the cited practice and leaves a major gap, it is only partially adequate.

**Deficiency excerpt**

> Review of R35's clinical record revealed: 8/17/22 - R35 was admitted to the facility. 4/30/24 - A physician's order for lisinopril 10 mg give one tablet by mouth one time a day for hypertension (high blood pressure). Hold for systolic blood pressure less than 100 and hold if heart rate is less than 60. 7/10/24 - The July MAR documented R35 had a blood pressure listed 120/77 and heart rate of 56 and a signature indicating lisinopril medication was administered. 7/11/24 - 7/23/24 - A pharmacist's medication regimen review documented that for R35, recommendation to the facility: '[R35] is receiving lisinopril 10mg with parameters to hold is systolic blood pressure (SBP) is less than 100 or heart rate (HR) less than 60 and was the medication was given (per MAR).' 9/20/24 - A physician's order for lisinopril 10 mg give 0.5 tablet by mouth one time a day for hypertension (high blood pressure).

**Plan excerpt**

> to the provider and response by the provider, daily x 14, weekly x 2, monthly x 2. Results will be reported through the QA process until 100% compliance has been achieved. A. RQ continues to reside at the facility. B. All residents have the potential to be affected by the deficient practice. C. RCA: provider was not made aware of results nor were they reviewed by the provider in electronic medical record. The facility contracted with a new lab service to ensure results are available to providers in the electronic medical record. Lab orders are documented in the record as well as tracked and reviewed at the daily clinical meeting. A document has been created to alert the Interdisciplinary Team of pending lab orders and remains active until the results have been received and communicated to the provider. Documentation of this process will be implemented in the resident record form in order
### cms2567_poc_319c03bda2c1 / F0812 / partial
- Facility: WESTMINSTER VILLAGE HEALTH
- Severity: E (potential_harm)
- Primary vs audit: partial / adequate (binary agree=False)
- Hidden correction metadata: Deficient, Provider has date of correction / 2024-12-09
- Reason: The plan responds to the cited kitchen sanitation and storage problems with immediate fixes, identifies all residents as potentially affected, and includes staff re-education plus a monitoring schedule. However, it is only partially adequate because the temperature-log deficiency is addressed in a generic way ('completed going forward') without a concrete corrective process for ensuring all required food temperatures are taken and documented, and it lacks a more specific systemic fix such as policy revision or competency checks. The plan also leaves some ambiguity about who is responsible for implementation and when the corrective actions begin.

**Deficiency excerpt**

> Based on observation and interview it was determined that the facility failed to ensure food was stored, prepared, and served in a manner that prevents food borne illness to the residents. Findings include: 10/21/24 9:14 AM - During the initial tour of the kitchen, there were no buckets containing sanitizing solution for storing wet wiping clothes used for sanitizing food preparation surfaces. 10/21/24 9:38 AM - During a tour of the kitchen, E12 (Cook) tested the sanitizing solution in the three compartment sink, directly at the source two times. Both attempts indicated the level of chemical concentration was not at a sufficient level to provide proper sanitization. An interview with E12 later that day revealed the facility had been using the incorrect type of chemical test strips when testing the sanitizer levels in the kitchen. 10/21/24 9:42 AM - During a tour of the kitchen, there wer

**Plan excerpt**

> No residents were affected by this practice. The sanitizing solution and buckets were prepared and put in place. The correct chemical test strips were obtained and used. The incorrect chemical test strips were disposed of. The cans with dented sides were removed from the building. There were no other dented cans identified. The ice scoop was removed from the ice machine, ice in the machine was disposed of and the machine was sanitized. All residents have the potential to be affected by this practice. The sanitizing solution and buckets were put in place. The correct chemical test strips were put in place. The incorrect chemical test strips were disposed of. The dented cans were removed. The ice scoop was removed, ice from the machine removed and ice machine were sanitized. The temperature log sheets were completed going forward. A root cause analysis revealed the need for re-education of
### cms2567_poc_40768811ddad / F0656 / partial
- Facility: REGENCY HEALTHCARE & REHAB CENTER
- Severity: E (potential_harm)
- Primary vs audit: partial / partial (binary agree=True)
- Hidden correction metadata: Deficient, Provider has date of correction / 2025-03-14
- Reason: The plan addresses the cited problems in a general way by updating R23 and R43 care plans, identifying at-risk residents, training staff, and auditing compliance. However, it is only partially adequate because the response to R89 is weak: it says the care plan could not be revised due to discharge, which does not fully address the cited deficient practice or show a corrective action for the resident's record. The plan also does not clearly demonstrate that the revised care plans include measurable objectives and timeframes, which was central to the deficiency, and the monitoring/timeline language is not fully concrete.

**Deficiency excerpt**

> Based on record review and interview, it was determined that for three (R23, R89 and R43) residents reviewed for care plans the facility failed to develop and implement person-centered care plans, that included measurable objectives and timeframes, to meet each residents' needs. Findings include: 1. R23's clinical record revealed: 11/8/24 - R23 was admitted to the facility. 11/9/24 7:41 AM - R23's admission evaluation documented: "... 8, Preferred Language: SPANISH 9. Do you need or want an interpreter to communicate with a doctor or health care staff? YES...". 11/14/24 - The admission MDS assessment, under Section A, incorrectly documented that R23's preferred language was English. From 11/8/24 through 1/7/25, R23 lacked a person-centered communication care plan as a Spanish-speaking resident. 1/8/25 - Two months after R23 was admitted to the facility, a care plan was initiated for comm

**Plan excerpt**

> R23 Comprehensive care plans were updated to reflect use of translation services for preferred language of Spanish. R89 Care Plan was unable to be revised to account for measurable objectives and timeframes to meet medical, mental and psychosocial needs as R89 has since discharged. R43 care plan has been updated with an updated personalized toileting program to assist in preventing falls. Residents with preferred languages other than English have the potential to be affected by this deficient practice. Additionally residents requiring person-centered activity plans to meet medical, mental and psychosocial needs have the potential to be affected by this deficient practice. Lastly residents requiring interventions and installation of a toileting program to prevent falls have the potential to be affected by this deficient practice. Facility educator or designee will in-service licensed nurs
### cms2567_poc_42fd4266643e / F0689 / partial
- Facility: ENUMCLAW HEALTH & REHAB CENTER
- Severity: D (potential_harm)
- Primary vs audit: partial / partial (binary agree=True)
- Hidden correction metadata: Deficient, Provider has date of correction / 2025-07-11
- Reason: The plan is not boilerplate and does respond to the cited fall-management deficiency with resident-specific review, care plan updates, staff education, and audits. However, it remains somewhat generic about what interventions were added for each resident and how the facility will ensure all post-fall care plans are promptly revised after every fall. The systemic monitoring is present, but the corrective detail is not fully concrete enough to be clearly adequate for the full scope of the cited deficiency.

**Deficiency excerpt**

> Based on interview, and record review, the facility failed to initiate interventions to prevent continued falls for 4 of 7 residents (Resident 28, 42, 3, & 26) reviewed for falls. This failure placed residents at risk of continued falls, potential neglect, and other negative health outcomes. According to a facility policy titled, "Resident Falls Management," when a resident had a fall the facility would develop an appropriate plan to minimize recurrence. The policy showed the facility would evaluate and modify plans to prevent the recurrence of falls. In an interview on 06/13/2025 at 11:34 AM, Staff B stated Resident 26's safety CP interventions needed to be updated and revised to reflect the current interventions. Refer to F610 - Investigate/Prevent/Correct Alleged Violation. According to a 05/28/2025 Admission Minimum Data Set (MDS - an assessment tool) Resident 28 admitted to the faci

**Plan excerpt**

> A. How the nursing home will correct the deficiency as it relates to the resident. 1. Resident #28 discharged /2025. 2. Resident #42, #3, fall investigation re-opened, analyzed the root cause of the fall and updated care plan to prevent repeat falls. 3. Resident #26 fall care reviewed and discontinued the care plan that bed placed against the wall reflects current interventions needed as the resident is ambulatory and does not need the bed against the wall. B. How the nursing home will act to protect residents in similar situations. 1. Facility reviewed resident falls in the last 2 weeks to ensure fall care plan interventions are placed in accordance with the root cause of the fall. No residents noted to have negative outcome related to the deficiency. C. Measures the nursing home will take or the systems will alter to ensure that the problem does not recur. 1. Re-education provided to E
