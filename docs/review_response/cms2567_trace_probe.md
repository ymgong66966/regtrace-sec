# CMS-2567 RegTrace Probe

This probe checks whether CMS-2567 nursing-home Statements of Deficiencies and
Plans of Correction can support a RegTrace-style cross-regulatory extension.

## Headline

- Zenodo deficiency rows: 17274
- Zenodo plan-of-correction rows: 11122
- Grouped `deficiency + plan_of_correction` pairs: 4226
- Pairs matched to CMS HealthCitations correction metadata: 2615
- Match rate among grouped pairs: 0.619
- High-trust matched pairs, min trust >= 0.8: 2588
- Matched pairs with non-empty correction date: 2611 / 2615
- Candidate JSONL: `data/cms2567/cms2567_regtrace_candidates.jsonl`

## Interpretation

CMS-2567 is structurally much closer to RegTrace-SEC than the FDA warning-letter
probe. It has regulator-authored deficiency narratives, provider-authored plans
of correction, provenance to public source PDFs, trust scores, and official CMS
correction-status metadata.

The main caveat is label design. In the matched subset, correction status is
heavily skewed toward `Deficient, Provider has date of correction`. This makes a
naive resolved/unresolved classification weak. The dataset is stronger for:

1. plan-of-correction adequacy review;
2. correction-delay or severity-aware adequacy prediction;
3. cross-domain testing of obligation-to-response review policies; and
4. external demonstration that RegTrace-style traces exist outside SEC filings.

It should not simply replace the SEC benchmark unless we construct task labels
that are not collapsed by the near-universal correction-date outcome.

## Outcome Distribution

| value | count |
| --- | ---: |
| Deficient, Provider has date of correction | 2557 |
| Past Non-Compliance | 47 |
| Deficient, Provider has plan of correction | 7 |
| No revisit needed | 3 |
| Waiver has been granted | 1 |

## High-Trust Outcome Distribution

| value | count |
| --- | ---: |
| Deficient, Provider has date of correction | 2530 |
| Past Non-Compliance | 47 |
| Deficient, Provider has plan of correction | 7 |
| No revisit needed | 3 |
| Waiver has been granted | 1 |

## High-Trust State Distribution

| value | count |
| --- | ---: |
| WA | 533 |
| DE | 352 |
| IN | 169 |
| SD | 165 |
| NM | 154 |
| MI | 129 |
| NC | 115 |
| ND | 115 |
| VA | 114 |
| WY | 111 |
| ID | 73 |
| NJ | 70 |
| DC | 68 |
| KY | 62 |

## High-Trust F-Tag Distribution

| value | count |
| --- | ---: |
| F0880 | 163 |
| F0812 | 128 |
| F0689 | 128 |
| F0684 | 102 |
| F0657 | 87 |
| F0656 | 83 |
| F0761 | 83 |
| F0641 | 71 |
| F0658 | 69 |
| F0695 | 56 |
| F0609 | 52 |
| F0550 | 50 |
| F0584 | 44 |
| F0842 | 43 |

## High-Trust Report-Year Distribution

| value | count |
| --- | ---: |
| 2025 | 1044 |
| 2024 | 774 |
| 2026 | 359 |
| 2023 | 326 |
| 2022 | 80 |
| 2021 | 3 |
| 2018 | 2 |

## Text Lengths

- Median deficiency text length, high-trust pairs: 2330.0
- Median plan-of-correction text length, high-trust pairs: 1071.5

## Samples

### Candidate 1: SURRY COMMUNITY HEALTH CENTER BY HARBORVIEW / F0550
- State: NC
- Survey date: 2024-03-27
- Outcome: Deficient, Provider has date of correction
- Correction date: 2024-04-24
- Scope/severity: G
- Source URL: https://info.ncdhhs.gov/dhsr/facilities/nh/2024/20240426-953479.pdf

**Deficiency excerpt**

> Based on record reviews, observations, resident, and staff interviews, the facility failed to protect residents' dignity when residents were left soiled in feces and saturated in urine for 2 of 2 residents reviewed for dignity issues (Resident #4 and Resident #305). When they were not provided incontinent care Resident #4 reported feeling unworthy of being looked at, sanitary rights being ignored, uncomfortable, and nasty; Resident #305 reported feeling cold, wet, and uncomfortable. Resident #4 was admitted to the facility on 6/22/23 with diagnoses including muscle weakness, neuromuscular dysfunction of the bladder, and the need for assistance with personal care. The Minimum Data Set (MDS) quarterly assessment dated 01/31/24 revealed Resident #4 was cognitively intact. She was incontinent of bowel, had an indwelling catheter, and required substantial maximum assistance by staff with toil

**Plan of correction excerpt**

> 1. Immediate action(s) taken for the resident(s) found to have been affected include: Resident #4 on 3/17/24 at 2pm received incontinence care per the resident. Resident #305 on 3/17/24 at approximately 330pm had received incontinence care and was clean and dry per the resident. 2. Identification of other residents having the potential to be affected was accomplished by: The facility determined that all incontinent residents have potential to be affected. 3. Actions taken/systems put into place to reduce the risk of future occurrence include: The VP of Clinical, Regional Nurse, Administrator, Director of Nursing, Assistant DON, and/or Unit manager will provide education beginning 4/18/2024 to all staff on the Quality of Life-Dignity policy and the importance of ensuring that Dignity is maintained with regards to timely incontinence care. All new Staff will be in serviced on these items a
### Candidate 2: SURRY COMMUNITY HEALTH CENTER BY HARBORVIEW / F0603
- State: NC
- Survey date: 2024-03-27
- Outcome: Deficient, Provider has date of correction
- Correction date: 2024-04-24
- Scope/severity: J
- Source URL: https://info.ncdhhs.gov/dhsr/facilities/nh/2024/20240426-953479.pdf

**Deficiency excerpt**

> Continued From page 55. Interview was performed on 3/17/24 at 12:06 PM with Medication Aide #4 who stated they typically left Resident #98's room door closed and did not like to wake her up because she would yell/scream all day and "ramp the other residents up". She stated the resident yelled and screamed when she was awake. Resident #98 was in a single occupied room and they usually kept her door closed in the morning and at night because other residents were trying to sleep. On 3/20/24 at 2:35 PM, NA #3 stated Resident #98 was originally able to propel her wheelchair by scooting herself with her feet but over the last 2 weeks had declined and could no longer scoot herself. She had never seen Resident #98 be able to open doors. Medication Aide #2 on 3/20/24 at 2:45 PM explained Resident #98 had declined in condition the last couple of weeks, had screaming/yelling behaviors and did not l

**Plan of correction excerpt**

> Clinical, Administrator, Unit Manager and/or Regional Nurse on the Identifying Involuntary Seclusion and Unauthorized Restraint policy and the Abuse, Neglect, and Exploitation policy which outlines types of abuse and reporting responsibilities and procedures to follow. The inservice will include the importance of keeping all residents free from involuntary seclusion. No resident, regardless of the situation, will be placed in any type of involuntary seclusion. All new Nurses, CNAs and MAs will be in serviced on these items and policies during the orientation process by the DON or ADON. Any Nurses, CNAs or MAs who have not gone through the training prior to the compliance date will have to do so prior to working again. Any agency staff will be educated prior to working. The ADON, Social Services Director, Regional Nurse and/or DON, beginning 4/18/24, will conduct an audit of all residents
### Candidate 3: SURRY COMMUNITY HEALTH CENTER BY HARBORVIEW / F0604
- State: NC
- Survey date: 2024-03-27
- Outcome: Deficient, Provider has date of correction
- Correction date: 2024-04-24
- Scope/severity: J
- Source URL: https://info.ncdhhs.gov/dhsr/facilities/nh/2024/20240426-953479.pdf

**Deficiency excerpt**

> Continued From page 83 - 3/20/24 the Social Worker, MDS Nurse and Regional Operations questioned all residents with BIMS above 8 if they have ever been restrained against their will. All residents stated that they have not been restrained.

**Plan of correction excerpt**

> The facility's policies and procedures on 'Identifying Involuntary Seclusion and Unauthorized Restraint' and the 'Abuse, Neglect and Exploitation' policy were reviewed on 3/20/24 at approximately 6:15pm by the DON, Administrator, Social Worker, ADON/IP, Regional Nurse Consultant, Regional Operations, and VP of Clinical. The VP of Clinical in-serviced the participants on the Identifying Involuntary Seclusion and Unauthorized Restraint policy and the Abuse, Neglect and Exploitation policy and importance ensuring all residents are kept free from Restraints and Abuse. Current medication aides, RNs, licensed nurses and CNAs will receive training on the Identifying Involuntary Seclusion and Unauthorized Restraint policy and the Abuse, Neglect, and Exploitation policy and the importance of ensuring all residents are kept free from unauthorized restraints. Inservice began on 3/20/24 at approxima
### Candidate 4: SURRY COMMUNITY HEALTH CENTER BY HARBORVIEW / F0697
- State: NC
- Survey date: 2024-03-27
- Outcome: Deficient, Provider has date of correction
- Correction date: 2024-04-24
- Scope/severity: K
- Source URL: https://info.ncdhhs.gov/dhsr/facilities/nh/2024/20240426-953479.pdf

**Deficiency excerpt**

> Based on observation, record review and resident, resident representative, Pharmacy, Medical Director (MD), Physician Assistant (PA), and staff interviews, the facility failed to address a resident's pain (Resident #21) after repeated reports to staff that she had not received her pain medications during the night shift (7:00 AM to 7:00 PM). Resident #21 reported starting the end of November 2023 she was told by Medication Aide (MA) #3 the facility had run out of her Methadone (analgesic opioid agonist), or MA #3 would tell her that she would bring her pain medication and never return during the night shift. Resident #21 informed the PA on 12/12/23 that her pain medications were not being given to her. On 1/05/24 Resident #21 was seen by the PA and reported increased pain primarily at night. Resident #21 reported when she was not administered her Methadone, she experienced terrible/awful

**Plan of correction excerpt**

> Resident #21's Medical Doctor (MD) was called on 3/21/24 and stated that it was unsafe to give her anymore pain medications at this time. The MD agreed and the resident agreed to be evaluated at a pain clinic. The resident visited the Bethany Pain Clinic on 4/9/24. The provider at the clinic would not see or adjust the resident's medication because of how high the residents dosage is already. The resident was interviewed by the DON on 4/22/24 again about seeing another pain clinic or doctor about her pain and she says that she does not want to go anywhere else at this time. Identification of other residents having the potential to be affected was accomplished by: The facility has determined that all residents have the potential to be affected. Actions taken/systems put into place to reduce the risk of future occurrence include: The DON, ADON and/or Regional Nurse
### Candidate 5: SURRY COMMUNITY HEALTH CENTER BY HARBORVIEW / F0842
- State: NC
- Survey date: 2024-03-27
- Outcome: Deficient, Provider has date of correction
- Correction date: 2024-04-24
- Scope/severity: D
- Source URL: https://info.ncdhhs.gov/dhsr/facilities/nh/2024/20240426-953479.pdf

**Deficiency excerpt**

> An interview conducted on 03/27/24 at 11:27 AM with Unit Manager #1 revealed she had entered the physician order dated 02/29/24 for intravenous (IV) fluids for Resident #255. The interview revealed she would have normally started the IV herself, however it was a busy day and she didn't get to it. She stated the supplemental fluids were ordered by the physician because the resident had a decrease in oral intake and was experiencing a decline. She stated she was in charge of the resident's hall on 02/29/24 and did not let the oncoming nurse know Resident #255 needed an IV started. The interview revealed she received a call from Nurse #6 on 03/01/24 who asked if Resident #255 had ever had an IV and were his fluids completed. She stated she did not know the answer to that question and that they would have to investigate further on Monday. The interview revealed she identified on Monday 03/04

**Plan of correction excerpt**

> 03/03/24 for the 7:00 to 3:00 PM shift. inservice will also cover ensuring that accurate documentation is completed by the RN or LPN regarding IV therapy. All new RNs and LPNs will be in serviced on these items and policies during the orientation process by the DON or ADON. Any Staff who have not went through the training prior to the compliance date will have to do so prior to working again. Any agency staff will be educated prior to working. The Director of Nursing (DON), ADON and/or Regional Nurse, beginning /18/2024, will review all intravenous fluid orders 5 days per week for 12 weeks to ensure all orders for intravenous fluids are implemented as ordered and documentation is completed accurately. Any deficient practice found during the audits will be corrected immediately and education and/or corrective action done by the DON as appropriate. The Audit findings will be reported by th
