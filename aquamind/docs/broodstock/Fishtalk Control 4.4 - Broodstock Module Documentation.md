# Fishtalk Control 4.4 - Broodstock Module Documentation

**Author:** Manus AI  
**Document Version:** Comprehensive Feature Documentation  
**Source:** Fishtalk Control 4.4 User Guide (Pages 177-205)  
**Date:** June 30, 2025

## Table of Contents

1. [Overview](#overview)
2. [Pit Tagging System](#pit-tagging-system)
3. [Trays and Stands Management](#trays-and-stands-management)
4. [Spawning Management](#spawning-management)
5. [Nursery Operations](#nursery-operations)
6. [Transfer and Logistics](#transfer-and-logistics)
7. [Hatching Process](#hatching-process)
8. [Reporting and Analytics](#reporting-and-analytics)
9. [System Configuration](#system-configuration)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The Broodstock module represents a sophisticated add-on component within the Fishtalk Control 4.4 system, specifically designed to address the complex requirements of hatchery operations and broodstock management in aquaculture facilities. This module requires additional licensing beyond the base Fishtalk system and provides comprehensive functionality for managing the entire lifecycle of fish breeding operations, from individual fish tracking through spawning, incubation, and hatching processes.

The primary purpose of the Broodstock module is to enable complete traceability throughout the entire breeding process, allowing operators to register all stages of egg fertilization and incubation while maintaining detailed records that can be cross-referenced over time to improve stock outcomes and breeding performance. This comprehensive tracking capability is essential for modern aquaculture operations that require detailed genetic and performance data to optimize their breeding programs and ensure the highest quality offspring.

The module's design philosophy centers around providing operators with the tools necessary to maintain genetic integrity, track performance metrics, and generate detailed reports that support data-driven decision making in breeding operations. By capturing detailed information at every stage of the breeding process, the system enables operators to identify patterns, track family lineages, and make informed decisions about future breeding strategies based on historical performance data.




## Pit Tagging System

The Pit Tagging system represents one of the most fundamental components of the Broodstock module, providing the capability to track individual fish throughout their entire lifecycle within the facility. This system is exclusively available with the Broodstock module and serves as the foundation for all individual fish tracking and traceability operations within the system.

### Individual Fish Registration

The pit tagging functionality allows for comprehensive registration of individual fish through both manual entry and automated file import processes. Each individual fish can be assigned a unique pit tag identifier that serves as the primary key for tracking that fish throughout its lifecycle within the facility. The system maintains detailed records of each individual's location, entry and exit times, and current status (active or terminated).

The registration process supports extensive customization through configurable parameters that can be defined under the Global Lists/Code list editor/Parameters for individual fish section. These parameters can be assigned various format types including Text, Date, Number, or Boolean (True/False) values, allowing operators to capture a wide range of data points specific to their operational requirements and research objectives.

### File Import Capabilities

The system provides robust file import functionality that enables operators to efficiently process large numbers of pit tag records from Excel files. The import process includes sophisticated mapping capabilities that allow operators to define how columns in their Excel files correspond to fields in the Fishtalk database. This mapping functionality is particularly valuable for operations that maintain their own data collection systems and need to integrate that data into the Fishtalk environment.

During the initial import process, operators must map Excel file columns to the appropriate Fishtalk database fields using dropdown menus. The system provides special handling for certain fields such as Sex, where operators can map the values found in their Excel files to the standardized values used within the Fishtalk system. For example, the letter "M" in an Excel file can be mapped to represent "Male" in the Fishtalk system.

The Individual ID field serves as a critical component of the import process, as it must be unique for each record since it functions as the primary key in the Fishtalk system. The system includes validation to prevent duplicate records and will identify and display conflicts when duplicate records are encountered during the import process.

### Template Management

To streamline repeated import operations, the system includes template management functionality that allows operators to save their field mapping configurations for future use. Once an operator has completed the initial mapping process for a particular file format, they can save this mapping as a named template. Subsequently, when importing files with the same structure, operators can simply select the saved template rather than repeating the entire mapping process.

This template functionality significantly reduces the time and effort required for routine data imports and helps ensure consistency in how data is processed across multiple import operations. The templates are stored within the system and can be reused indefinitely, making them particularly valuable for operations that regularly receive data in standardized formats.

### Search and Query Functionality

The pit tagging system includes comprehensive search and query capabilities that enable operators to locate and analyze individual fish records based on various criteria. The search interface provides multiple filtering options including organization-based filters, date-based parameters, and status filters that allow operators to focus on specific subsets of their fish population.

Operators can filter records to include only active individuals, only terminated individuals, or both, depending on their analysis requirements. The system also supports date-based filtering that enables operators to examine fish populations during specific time periods or track changes in population composition over time.

The search results are displayed in a grid format that provides comprehensive information about each individual fish, including their current location, entry and exit information, and current status. The grid interface supports editing capabilities, allowing operators to update individual records directly from the search results interface.

### Data Export and Reporting

The pit tagging system includes built-in export and reporting capabilities that enable operators to extract data for external analysis or reporting purposes. The system provides options to print or export search results, giving operators flexibility in how they utilize the data collected through the pit tagging system.

Exit row information is automatically maintained within the system, displaying details about when individuals are registered as killed during spawning registrations or other mortality events. This information provides valuable insights into the lifecycle of individual fish and supports comprehensive mortality tracking and analysis.


## Trays and Stands Management

The Trays and Stands management system provides a hierarchical organizational structure that enables operators to maintain detailed tracking of fish groups at a granular level within their facilities. This system is particularly important for hatchery operations where eggs and fry are maintained in specific physical locations that must be tracked for operational and regulatory purposes.

### Hierarchical Organization Structure

The system implements a three-tier organizational hierarchy consisting of Sites, Stands, and Trays. Sites represent the highest level of organization, typically corresponding to physical facilities or major operational areas. Within each site, Stands can be added to represent groupings of related equipment or operational areas. Finally, Trays represent the most granular level of organization, corresponding to individual containers or holding units within each stand.

This hierarchical structure provides operators with the flexibility to organize their operations in a manner that reflects their physical infrastructure and operational procedures. The system maintains the relationships between these organizational levels, enabling operators to perform operations at any level of the hierarchy while maintaining appropriate data integrity and traceability.

### Stand Configuration and Management

Stands serve as intermediate organizational units that contain multiple trays and provide a convenient level of aggregation for many operational activities. When adding stands to a site, operators can assign descriptive names that reflect the physical layout or operational purpose of each stand. The system automatically creates the organizational relationships and makes the stands available for use in spawning registrations and other operational activities.

The stand configuration process is designed to be completed prior to importing spawning record files, as stands and trays cannot be mapped during the file import process. This requirement ensures that the organizational structure is properly established before operational data is imported, maintaining data integrity and preventing organizational inconsistencies.

Each stand can contain multiple trays, and the system maintains the relationships between stands and their constituent trays throughout all operational processes. This relationship enables operators to perform operations at the stand level that are automatically distributed to all trays within that stand, significantly streamlining data entry and operational procedures.

### Tray Management and Tracking

Trays represent the most detailed level of organization within the system and correspond to individual physical containers or holding units where fish or eggs are maintained. Each tray within a stand can be individually named and tracked, providing operators with precise control over their inventory and operational procedures.

The tray management system supports detailed tracking of contents, enabling operators to maintain accurate records of what is contained in each tray at any given time. This granular tracking capability is essential for maintaining genetic integrity, tracking family lineages, and ensuring that operational procedures are applied to the correct groups of fish or eggs.

When performing operations such as spawning registrations, nursery activities, or transfers, operators can specify the exact tray locations for their activities. The system maintains these location records and uses them to provide detailed traceability information throughout the lifecycle of the fish or eggs.

### Integration with Spawning Operations

The Trays and Stands system is closely integrated with spawning operations, enabling operators to specify exact locations for spawning products during the registration process. When spawning records are created, operators can assign the resulting eggs to specific stands and trays, maintaining precise location tracking from the moment of fertilization.

This integration ensures that spawning products are properly tracked from their creation through all subsequent operations. The system maintains the location information and uses it to support transfer operations, nursery registrations, and other activities that require precise location tracking.

The spawning integration also supports the specification of stands and trays during file import operations, provided that the organizational structure has been properly established prior to the import process. This capability enables operators to maintain location tracking even when processing large volumes of spawning data through automated import procedures.

### Operational Efficiency Features

The Trays and Stands system includes several features designed to improve operational efficiency and reduce the time required for data entry. Operations can be performed at the stand level and automatically distributed to all trays within that stand, eliminating the need to enter the same information multiple times for related trays.

The system also supports bulk operations that enable operators to perform the same action across multiple stands or trays simultaneously. This capability is particularly valuable for operations such as treatments, environmental parameter recording, or other activities that are typically applied to multiple locations at the same time.

Navigation within the organizational hierarchy is streamlined through the use of expandable tree structures that allow operators to quickly locate specific stands and trays. The system maintains the organizational relationships and provides visual cues to help operators understand the structure and relationships within their facility organization.


## Spawning Management

The Spawning Management system represents the core functionality of the Broodstock module, providing comprehensive capabilities for registering and tracking the entire spawning process from individual fish selection through egg fertilization and input into the production system. This system enables operators to maintain complete genetic integrity and traceability while supporting sophisticated breeding programs and performance analysis.

### Spawning Process Overview

The spawning registration process is designed to capture all critical information about the breeding process while maintaining flexibility to accommodate various operational procedures and timing constraints. The system recognizes that screening results for male and female fish may not be available at the time of initial registration, allowing operators to complete the registration in stages as information becomes available.

The spawning process is divided into five distinct stages: Entry of the Spawn ID, Male Individual Selection, Female Individual Selection, Fertilization mapping, and Input of resulting eggs. This staged approach enables operators to work through the registration process systematically while ensuring that all critical information is captured and properly associated with the spawning event.

Each spawning registration maintains complete traceability of which female eggs and male milt have been combined, ensuring that genetic integrity is preserved and that detailed family lineage information is available for future analysis and breeding decisions. The system automatically calculates various metrics including eggs per kilogram ratios and survival rates, providing operators with immediate feedback on the performance of their breeding operations.

### Spawn ID Management

The Spawn ID serves as the primary identifier for each spawning event and provides operators with flexibility in how they organize and reference their spawning activities. The system automatically defaults the Spawn ID to the date selected in the Activity calendar when the spawning form is launched, but this field is fully editable to accommodate various organizational and record-keeping requirements.

Operators can enter any combination of alphanumerical text to create Spawn IDs that align with their operation's normal record-keeping format. This flexibility enables operations to maintain consistency with existing record-keeping systems while taking advantage of the enhanced capabilities provided by the Fishtalk system.

The Spawn ID becomes a permanent part of the spawning record and is used throughout the system to reference the specific spawning event. This identifier appears in reports, transfer records, and other system functions, providing a consistent reference point for all activities related to the spawning event.

### Male Individual Selection Process

The male individual selection process provides comprehensive functionality for selecting and tracking male fish used in spawning operations. Operators can select males from multiple units within their facility, with the system maintaining detailed records of the source unit, individual identification, and various performance metrics for each male fish.

The selection process begins with choosing the unit from which males are to be selected and specifying the number of male individuals to be included in the spawning operation. The system automatically creates individual records for each male fish, assigning default Tag/ID values based on numerical sequencing that can be customized to match the operation's tagging scheme.

Individual fish information is automatically populated based on the source unit's average weight calculations, but operators can edit these values if detailed weight measurements are performed during the spawning process. The system provides four free text comment fields for each individual male, enabling operators to capture specific observations or notes about individual fish performance or characteristics.

The system includes comprehensive tracking of fish disposition, allowing operators to specify whether each male will be returned to the unit after milt collection or will be removed from the population. Fish that are not returned are automatically accounted for in the unit's population and weight calculations, maintaining accurate inventory records.

Screening functionality enables operators to identify males that have been disqualified due to disease screening or other factors. When a male is marked as positively screened, the system requires selection of a culling cause and automatically prevents the fish from being returned to the unit. The system also provides visual indicators when positively screened males are used in fertilization, helping operators identify egg batches that must be culled.

### Female Individual Selection Process

The female individual selection process mirrors many aspects of the male selection process while incorporating additional functionality specific to egg production and quality assessment. Female selection includes comprehensive tracking of egg production metrics, mortality rates, and quality indicators that are essential for evaluating breeding performance and making informed decisions about egg utilization.

The selection process includes detailed tracking of initial egg production results, including the volume of eggs stripped (measured in liters) and the estimated number of eggs per liter. These measurements enable the system to calculate total egg production and eggs per kilogram ratios, providing immediate feedback on female performance and fecundity.

The system incorporates a two-stage assessment process that recognizes the reality of hatchery operations where initial egg quality assessments may be refined as additional information becomes available. The Initial Result section captures immediate post-stripping measurements, while the Verified Result section allows operators to record mortality rates and adjusted egg counts after the first 24-hour period.

Mortality tracking in the Verified Result section enables operators to record the percentage of eggs that are lost during the critical first 24 hours after stripping. The system automatically calculates adjusted egg counts based on these mortality rates, ensuring that subsequent operations are based on accurate egg availability rather than initial production estimates.

Female screening functionality operates similarly to male screening, with the system providing visual indicators and automatic culling calculations when females are identified as positively screened. The system maintains the flexibility to add screening information after the initial registration, recognizing that screening results may not be immediately available.

### Fertilization Mapping and Genetic Integrity

The fertilization mapping process represents one of the most critical aspects of the spawning registration, as it establishes the genetic relationships that will be maintained throughout the lifecycle of the resulting offspring. The system provides sophisticated functionality for mapping male and female pairs while maintaining visual indicators of any issues that could compromise genetic integrity.

The mapping process allows operators to specify which males have been used to fertilize each female's egg batch, with support for multiple males per female when appropriate for the breeding program. The system automatically expands the grid interface to accommodate multiple male entries per female, providing flexibility for various breeding strategies.

Visual indicators play a crucial role in maintaining genetic integrity during the fertilization mapping process. When males or females that have been marked as positively screened are included in fertilization mappings, the system highlights these combinations in red, providing immediate visual feedback that these egg batches must be culled to prevent compromised genetics from entering the production system.

The system includes efficiency features for mapping operations, including the ability to select multiple females and apply the same male or combination of males to all selected records. This bulk mapping capability significantly reduces data entry time for operations that use standardized breeding protocols or when the same male is used across multiple female egg batches.

Clearing and correction functionality enables operators to remove incorrect mappings or clear entire sections of the fertilization matrix when changes are needed. The system provides both selective clearing for specific records and bulk clearing for entire sections, giving operators flexibility in correcting mapping errors or adjusting breeding plans.

### Input Process and Production Integration

The input process represents the final stage of spawning registration and serves as the bridge between the breeding operation and the production system. This process transfers the fertilized eggs from the spawning registration into active production units where they will be tracked through incubation, hatching, and subsequent production phases.

The input process automatically populates unit assignments, dates, times, and egg quantities based on the information captured during the earlier stages of the spawning registration. This automation reduces data entry requirements and helps ensure consistency between the spawning records and the production system.

Project assignment during the input process enables operators to associate the spawning results with specific production projects, facilitating project-based tracking and analysis. The system automatically populates species and year class information based on the selected input project, maintaining consistency with production planning and tracking systems.

Supplier information can be specified during the input process, enabling operations that work with multiple breeding programs or external suppliers to maintain appropriate attribution and traceability. This information becomes part of the permanent record and is available for reporting and analysis purposes.

The input process includes selection of broodstock designation, fish type, and production phase information that becomes part of the permanent production record. These classifications are essential for tracking different genetic lines, production purposes, and operational phases throughout the production cycle.

### File Import Capabilities for Spawning Data

The system provides comprehensive file import capabilities that enable operators to process large volumes of spawning data efficiently while maintaining the same level of detail and traceability as manual registrations. The import process requires minimum information including Female Individual ID or Pit Tag and Male Individual ID or Pit Tag, but can accommodate additional data fields as available.

The import process includes sophisticated mapping functionality that enables operators to define how columns in their Excel files correspond to fields in the Fishtalk database. This mapping capability supports spawning date information, additional male assignments, and stand/tray specifications, providing flexibility for operations with varying data collection and organization requirements.

Template management for spawning imports operates similarly to pit tag import templates, enabling operators to save mapping configurations for repeated use. This functionality is particularly valuable for operations that regularly receive spawning data in standardized formats from multiple sources or collection systems.

After importing the basic spawning data, operators must still complete the detailed spawning parameters including egg volumes, eggs per liter estimates, and input project assignments. This hybrid approach enables efficient processing of large data volumes while ensuring that all critical operational parameters are properly specified and validated.

The import process automatically populates the male and female individual grids and creates the fertilization matrix based on the imported data. This automation significantly reduces data entry time while maintaining the same level of detail and traceability as manual registrations.


## Nursery Operations

The Nursery Operations system provides comprehensive functionality for managing the daily activities and maintenance requirements during the critical incubation period following spawning. This system enables operators to register and track mortality, culling, treatments, environmental parameters, and shocking procedures while maintaining detailed records that support performance analysis and regulatory compliance.

### Nursery Registration Framework

The nursery registration system is organized around a tabbed interface that groups related activities for efficient data entry and management. The system supports registration at both stand and tray levels, providing operators with flexibility in how they organize and record their daily activities. Data entered at the stand level is automatically distributed to underlying trays according to proportional algorithms, while tray-level entries provide precise control for specific situations.

The registration framework includes direct links to the primary global lists used in nursery operations, including Mortality Causes, Culling Causes, and Environment Parameters. These links enable operators to quickly access and update the available parameters without leaving the registration interface, streamlining the data entry process and ensuring that appropriate categories are available for all registration activities.

The system maintains complete integration with the organizational hierarchy established through the Trays and Stands system, enabling operators to work at the appropriate level of detail for their specific operational requirements. The expandable grid interface provides clear visual organization of stands and trays while supporting efficient navigation and data entry across multiple organizational levels.

### Mortality Registration and Tracking

Mortality registration provides comprehensive functionality for tracking and analyzing egg losses during the incubation period. The system enables operators to record mortality by specific causes, providing detailed information that supports performance analysis and process improvement initiatives. Mortality can be registered at either the stand level for broad distribution across trays or at the individual tray level for precise tracking.

When mortality is registered at the stand level, the system automatically distributes the mortality numbers across all trays within the stand according to the proportional egg populations in each tray. This distribution algorithm ensures that mortality is allocated appropriately while reducing data entry requirements for operations that experience uniform mortality patterns across related trays.

The mortality tracking system maintains detailed records of mortality causes, enabling operators to identify patterns and trends that may indicate environmental issues, disease problems, or other factors affecting egg survival. This information is essential for implementing corrective actions and improving overall hatchery performance.

Individual tray-level mortality registration provides precise control for situations where mortality patterns vary significantly between trays or where specific issues affect only certain portions of the egg population. This granular tracking capability enables operators to maintain accurate records even in complex situations involving multiple mortality causes or varying environmental conditions.

The system automatically updates egg population counts based on mortality registrations, ensuring that subsequent operations and calculations are based on accurate population estimates. This automatic updating eliminates the need for manual population adjustments and reduces the risk of errors in population tracking.

### Culling Operations Management

Culling operations represent planned removals of eggs or egg groups based on quality assessments, genetic screening results, or other operational decisions. The culling registration system provides comprehensive functionality for tracking these planned removals while maintaining detailed records of the reasons and quantities involved.

The culling system operates similarly to mortality registration in terms of stand-level versus tray-level entry options, but focuses on planned removals rather than natural losses. Culling causes are maintained as a separate category from mortality causes, enabling operators to distinguish between planned operational decisions and unplanned losses in their analysis and reporting.

Stand-level culling registration automatically distributes culling quantities across trays within the stand according to proportional egg populations, providing efficiency for operations that implement uniform culling decisions across related egg groups. This distribution capability is particularly valuable when culling decisions are based on genetic screening results that affect entire family groups.

Individual tray-level culling registration enables precise control for situations where culling decisions vary between trays or where specific quality issues affect only certain portions of the egg population. This granular control is essential for maintaining genetic integrity and ensuring that culling decisions are implemented precisely as intended.

The culling system maintains complete integration with the spawning registration system, enabling operators to implement culling decisions based on positive screening results for parent fish. When spawning registrations indicate positive screening for males or females, the corresponding egg batches can be efficiently identified and culled through the nursery registration system.

### Environmental Parameter Monitoring

Environmental parameter registration provides functionality for recording and tracking the environmental conditions experienced by incubating eggs. While these registrations are simplified compared to the full sensor registration capabilities available in other parts of the Fishtalk system, they provide essential data for analysis and regulatory compliance purposes.

The environmental parameter system enables operators to record key environmental factors such as temperature, dissolved oxygen, pH, and other parameters that affect egg development and survival. These parameters are maintained as configurable lists that can be customized to match the specific monitoring requirements of each operation.

Stand-level environmental parameter entry automatically copies the recorded values to all trays within the stand, providing efficiency for operations where environmental conditions are uniform across related egg groups. This copying functionality reduces data entry requirements while ensuring that environmental data is available at the tray level for detailed analysis.

Individual tray-level environmental parameter entry provides precise control for situations where environmental conditions vary between trays or where specific monitoring requirements apply to certain egg groups. This granular capability is essential for research operations or situations where environmental conditions are actively manipulated for specific egg groups.

The environmental parameter data becomes available throughout the Fishtalk system for reporting and analysis purposes, enabling operators to correlate environmental conditions with performance outcomes and identify optimal conditions for egg development and survival.

### Treatment Administration and Tracking

Treatment registration provides comprehensive functionality for recording and tracking therapeutic interventions applied to incubating eggs. The system maintains detailed records of treatment causes, medications used, concentrations, and quantities, providing complete documentation for regulatory compliance and performance analysis purposes.

The treatment system includes configurable lists for treatment causes and medications that can be customized to match the specific therapeutic protocols and regulatory requirements of each operation. These lists are maintained through the global lists system and can be updated as new treatments become available or regulatory requirements change.

Stand-level treatment registration enables operators to apply the same treatment protocol to all trays within a stand, providing efficiency for treatments that are applied uniformly across related egg groups. The system automatically copies treatment information to all trays within the selected stand, reducing data entry requirements while maintaining detailed records at the tray level.

Individual tray-level treatment registration provides precise control for situations where treatment protocols vary between trays or where specific therapeutic interventions are required for certain egg groups. This granular control is essential for research operations or situations where treatment protocols are tailored to specific conditions or requirements.

The treatment system includes functionality for treating multiple stands simultaneously, enabling operators to efficiently implement treatment protocols that span multiple organizational units. This bulk treatment capability is particularly valuable for facility-wide treatments or when responding to widespread health issues.

Copy functionality within the treatment system enables operators to replicate treatment protocols across selected trays, reducing data entry requirements when the same treatment is applied to multiple locations. This functionality supports efficient implementation of standardized treatment protocols while maintaining detailed records of all applications.

### Shocking Procedures and Documentation

Shocking registration provides specialized functionality for recording and tracking shocking procedures applied to incubating eggs. Shocking is a critical procedure in many hatchery operations that affects egg development and survival, requiring detailed documentation for operational and regulatory purposes.

The shocking registration system captures essential information including the timing of shocking procedures, methods used, personnel responsible, and estimated mortality and survival outcomes. This comprehensive documentation supports performance analysis and regulatory compliance while providing operators with feedback on the effectiveness of their shocking procedures.

Method selection for shocking procedures is maintained through configurable global lists that can be customized to match the specific protocols and equipment used by each operation. This flexibility enables the system to accommodate various shocking methodologies while maintaining standardized documentation and reporting capabilities.

Personnel tracking for shocking procedures enables operators to maintain records of who performed each procedure, supporting training documentation and quality assurance programs. The system includes functionality for adding new contacts to the personnel list directly from the shocking registration interface, streamlining the documentation process.

Mortality and survival estimation functionality provides immediate feedback on the effectiveness of shocking procedures. Operators can enter estimated numbers of dead eggs, with the system automatically calculating deviation values and survival rates based on the initial egg populations and estimated mortality.

The survival rate calculation provides immediate feedback on shocking effectiveness and enables operators to identify procedures or conditions that produce optimal results. This information is essential for refining shocking protocols and training personnel to achieve consistent results.

### Nursery Registration Reporting

The nursery registration system includes comprehensive reporting functionality that enables operators to export daily registrations to Excel format or generate on-screen summaries of registration activities. This reporting capability is essential for operations that require detailed documentation of daily activities for regulatory compliance or performance analysis purposes.

The reporting system provides preview functionality that displays only the stands and trays that have been included in registrations and only the activities that have been recorded. This filtered view eliminates blank entries and provides a clear summary of actual registration activities, making it easier to review and verify the completeness of daily records.

Export functionality enables operators to save registration data in Excel format for external analysis or integration with other systems. This export capability is particularly valuable for operations that maintain comprehensive databases or perform detailed statistical analysis of hatchery performance.

The reporting system maintains integration with the organizational hierarchy, enabling operators to generate reports at various levels of detail depending on their specific requirements. Reports can include stand-level summaries or detailed tray-level information, providing flexibility for different reporting and analysis needs.


## Transfer and Logistics

The Transfer and Logistics system provides comprehensive functionality for managing the movement of eggs and fish between different organizational units within the facility. This system maintains complete traceability while supporting the complex logistics requirements of modern hatchery operations, including stand and tray level transfers and specialized shuffle operations.

### Stand and Tray Level Transfers

The transfer system is fully integrated with the Trays and Stands organizational hierarchy, enabling operators to perform transfers at the appropriate level of granularity for their specific operational requirements. When performing transfers involving fishgroups that are organized using stands and trays, the system automatically displays the stand and tray information in the transfer interface, providing clear visibility of source and destination locations.

Transfer operations can be performed between individual trays, between stands, or between different organizational levels depending on the specific requirements of the operation. The system maintains complete traceability of all transfer activities, ensuring that the movement history of eggs and fish is preserved throughout their lifecycle within the facility.

The visualization section of the transfer interface provides clear identification of stands and trays using a standardized naming convention where entries are displayed as "Stand-Tray" (for example, "5-10" represents Stand 5, Tray 10). This naming convention provides immediate visual identification of source and destination locations while maintaining consistency across all transfer operations.

Grouping functionality enables operators to zoom between different organizational levels depending on their specific requirements. The Group Stands checkbox allows operators to switch between stand-level and unit-level views, providing flexibility for operations that need to work at different levels of organizational detail.

The transfer system maintains complete integration with the broader Fishtalk inventory management system, ensuring that all transfers are properly reflected in population counts, biomass calculations, and other inventory metrics. This integration eliminates the need for manual inventory adjustments and reduces the risk of errors in population tracking.

### Shuffle Tray Operations

The Shuffle Tray registration system provides specialized functionality for reorganizing tray contents within stands to optimize space utilization and maintain operational efficiency. This system addresses the common hatchery requirement to consolidate tray contents when some trays are emptied through culling or mortality events.

The shuffle operation is designed to move all eggs from one tray to another empty tray within the same stand, enabling operators to consolidate their egg populations and eliminate gaps in their stand organization. This consolidation is essential for maintaining efficient space utilization and ensuring that heating, aeration, and other environmental systems operate optimally.

The shuffle registration process requires that at least one tray within the stand has been emptied through previous culling or mortality registrations. This requirement ensures that destination trays are available for the shuffle operation and prevents conflicts with existing egg populations.

The shuffle interface displays all trays within the selected stand that contain eggs, enabling operators to specify destination trays for each source tray. The system maintains complete traceability of the shuffle operations, ensuring that the movement history is preserved and that subsequent operations can be properly tracked.

When shuffle registrations are saved, the system processes the movements in a systematic sequence that prevents conflicts and ensures that all movements are completed successfully. The automated processing eliminates the need for operators to manually coordinate multiple individual transfers and reduces the risk of errors in complex reorganization operations.

The shuffle system maintains complete integration with the nursery registration system, ensuring that subsequent mortality, culling, treatment, and other operations can be properly applied to the reorganized tray contents. This integration preserves the operational continuity that is essential for effective hatchery management.

## Hatching Process

The Hatching Process system provides comprehensive functionality for managing the transition from incubating eggs to live fish stock within the production system. This system enables operators to track hatching progress, update production stages, and maintain complete traceability as eggs develop into actively growing fish populations.

### Hatching Status Management

The hatching status management system provides comprehensive functionality for tracking the progress of egg development and the transition to live fish stock. The system automatically identifies all units within the facility that contain stocked eggs and displays comprehensive information including egg totals, species information, broodstock details, and other relevant data.

The hatching interface provides automatic population of site information based on the site portal from which the form is launched, but includes flexibility to change this information if transfers or other operations require different site assignments. This flexibility ensures that hatching registrations can be properly associated with the correct operational locations.

Year of hatch functionality provides specialized capability for operations where the calendar year of hatching differs from the production year class. This situation commonly occurs for egg groups that are hatched just before or after the new year, requiring special tracking to maintain consistency with production planning and market timing requirements.

The year of hatch designation becomes a permanent attribute that follows the fish stock through all subsequent production phases, including the marine group stage. This permanent association ensures that year class tracking remains accurate throughout the entire production cycle, supporting market planning and regulatory compliance requirements.

### Hatching Progress Tracking

Hatching progress tracking enables operators to monitor and record the development of their egg populations as hatching occurs over time. The system supports incremental progress recording, recognizing that hatching typically occurs over multiple days and requires ongoing monitoring and documentation.

Estimated progress recording enables operators to specify the percentage of eggs that have hatched at any given time, providing detailed tracking of hatching progress and enabling analysis of hatching patterns and timing. The system supports the use of function keys to copy progress estimates across multiple units, reducing data entry requirements for operations with uniform hatching patterns.

Multiple day hatching support recognizes that hatching events typically extend over several days and require ongoing monitoring and adjustment. When hatching registrations are created on different days, the system displays the last estimated progress percentage, enabling operators to track cumulative progress and make appropriate adjustments to their estimates.

The 100% completion threshold represents a critical milestone in the hatching process, as it indicates that all viable eggs have completed hatching and the population can be transitioned to active fish stock status. When 100% hatching is recorded, the system enables production stage changes and other transitions that reflect the new status of the population.

### Production Stage Transition

Production stage transition functionality enables operators to update the production classification of their populations as they complete the hatching process and begin active growth phases. This transition is essential for maintaining accurate production tracking and ensuring that appropriate management protocols are applied to the developing fish populations.

The production stage change capability becomes available when 100% hatching progress is recorded, ensuring that transitions occur only when the hatching process is complete. This requirement prevents premature transitions that could result in inappropriate management protocols being applied to populations that are still completing the hatching process.

Average weight specification during the hatching transition enables operators to establish initial weight parameters for the newly hatched fish populations. This weight information is essential for biomass calculations, feeding protocols, and other management activities that depend on accurate population and weight data.

The weight and biomass updates that occur during the production stage transition ensure that the newly hatched fish populations are properly integrated into the broader production management system. These updates provide the foundation for subsequent growth tracking, feeding management, and other production activities.

### Degree Day Calculations

Degree day calculation functionality provides sophisticated tracking of thermal development units that are essential for predicting and managing fish development timing. The system maintains accumulated degree day calculations from fertilization through hatching, providing comprehensive thermal history information.

The "Start Counting day degrees since hatching" option enables operators to begin tracking post-hatching thermal development, which is essential for predicting feeding timing, transfer schedules, and other management activities that depend on developmental stage rather than calendar time.

Accumulated degree day calculations are based on the initial stocking information and environmental data recorded throughout the incubation period. This comprehensive calculation provides accurate thermal history information that supports precise management timing and developmental stage assessment.

The degree day tracking system maintains integration with the environmental parameter recording system, ensuring that temperature data recorded through nursery registrations contributes to accurate degree day calculations. This integration provides comprehensive thermal tracking without requiring duplicate data entry.

### Stock Integration and Traceability

Stock integration functionality ensures that newly hatched fish populations are properly incorporated into the broader production management system while maintaining complete traceability to their breeding origins. This integration is essential for maintaining genetic integrity and supporting performance analysis throughout the production cycle.

The transition from egg status to active fish stock status involves comprehensive updates to population counts, biomass calculations, and production classifications. These updates ensure that the newly hatched populations are properly recognized by all system components and that appropriate management protocols are automatically applied.

Traceability maintenance throughout the hatching process ensures that the genetic and breeding information captured during spawning registrations remains associated with the resulting fish populations. This traceability is essential for breeding program analysis, performance evaluation, and regulatory compliance requirements.

The stock integration process maintains complete compatibility with the broader Fishtalk production management system, ensuring that hatched fish populations can be seamlessly managed through subsequent production phases including feeding, growth tracking, health management, and harvest planning.


## Reporting and Analytics

The Reporting and Analytics system provides comprehensive functionality for analyzing breeding performance, tracking family lineages, and generating detailed reports that support data-driven decision making in breeding operations. This system includes specialized reports that are specifically designed to address the unique analysis requirements of broodstock management and genetic tracking.

### Family Tree Reporting

The Family Tree Report provides sophisticated graphical visualization of genetic relationships and family lineages within the breeding program. This report enables operators to visualize complex genetic relationships and track the performance of specific family lines over time, supporting informed breeding decisions and genetic management strategies.

The family tree visualization includes comprehensive drill-down capabilities that enable operators to access detailed information about individual pit tagged fish and their relationships within the broader family structure. This detailed access is essential for understanding the genetic contributions of specific individuals and evaluating the performance of different genetic lines.

Selection functionality for the family tree report provides flexibility in defining the scope and focus of the analysis. Operators can select specific organization units, date ranges, and individual fish or fish groups depending on their specific analysis requirements. This flexibility enables both broad population analysis and focused evaluation of specific genetic lines or breeding events.

The report interface includes options for displaying fish groups, individual fish, or single individuals, providing different levels of detail depending on the analysis requirements. Legend display options enable operators to control the visual complexity of the report and focus on the most relevant information for their specific analysis needs.

Graphical connection visualization provides clear representation of the relationships and events that connect different fish groups and individuals within the breeding program. This visualization is essential for understanding complex genetic relationships and identifying patterns that may not be apparent in tabular data presentations.

The family tree report maintains complete integration with the pit tagging system, ensuring that individual fish identification and tracking information is accurately represented in the genetic relationship visualizations. This integration provides comprehensive traceability from individual fish through family relationships to population-level breeding outcomes.

### Chain of Custody Reporting

The Chain of Custody Report provides detailed tracking of facility and tank movements for specific spawning events, enabling operators to maintain complete traceability of fish populations from breeding through production phases. This report is essential for regulatory compliance and quality assurance programs that require detailed documentation of fish movement and handling.

The chain of custody reporting process begins with selection of specific spawning records based on date ranges and facility locations. The system displays all applicable spawning records for the selected criteria, enabling operators to focus their analysis on specific breeding events or time periods.

Family ID specification functionality enables operators to choose between using Fish Group Names or Year of Hatch as the primary identifier for tracking purposes. This flexibility accommodates different organizational and tracking requirements while maintaining consistency with existing record-keeping systems and regulatory requirements.

Detailed chain of custody information includes comprehensive tracking of spawn dates, family identifications, female and male complex identifications, spawning facilities, incubation facilities, delivery dates, and incubation tank assignments. This comprehensive information provides complete documentation of the handling and movement history for each spawning event.

The chain of custody report maintains complete integration with the organizational hierarchy system, ensuring that facility and tank assignments are accurately represented and that movement tracking reflects the actual physical locations and handling procedures used throughout the production process.

Information icon functionality provides access to detailed information about specific entries within the chain of custody report, enabling operators to drill down into specific events or movements for detailed analysis or documentation purposes. This detailed access is essential for investigating specific issues or providing comprehensive documentation for regulatory or quality assurance purposes.

### Spawning Overview Reporting

The Spawning Overview Report provides comprehensive summary information about specific spawning events registered within the system, enabling operators to analyze breeding performance and identify patterns or trends in their spawning operations. This report is essential for evaluating breeding program effectiveness and making informed decisions about future breeding strategies.

The spawning overview reporting process begins with selection of specific time periods and facility locations, enabling operators to focus their analysis on relevant spawning events. The system displays all applicable fish group records for the selected criteria, providing a comprehensive view of breeding activity during the specified period.

Fish group selection functionality enables operators to choose specific breeding groups for detailed analysis, providing flexibility to focus on particular genetic lines, breeding strategies, or performance characteristics. This selection capability is essential for targeted analysis of breeding program components and evaluation of specific breeding decisions.

Detailed spawning information includes comprehensive data about spawn dates, family identifications, female and male identifications, spawning facilities, and incubation facilities. This information provides complete documentation of breeding events and enables analysis of breeding patterns, facility utilization, and genetic management strategies.

The spawning overview report maintains complete integration with the spawning registration system, ensuring that all registered spawning events are accurately represented and that performance data reflects actual breeding operations and outcomes.

Report generation functionality provides immediate access to comprehensive spawning summaries, enabling operators to quickly assess breeding activity and identify areas that may require attention or further analysis. This immediate access is essential for maintaining effective oversight of breeding operations and ensuring that breeding programs remain on track to meet production and genetic objectives.

### Performance Analysis Capabilities

The reporting system includes comprehensive performance analysis capabilities that enable operators to evaluate breeding program effectiveness and identify opportunities for improvement. These analysis capabilities are essential for maintaining competitive breeding programs and ensuring that genetic management strategies produce optimal results.

Cross-referencing functionality enables operators to correlate breeding performance with subsequent production outcomes, including growth rates, disease resistance, and harvest performance. This correlation capability is essential for evaluating the long-term effectiveness of breeding decisions and identifying genetic lines that produce superior production outcomes.

Trend analysis capabilities enable operators to identify patterns in breeding performance over time, supporting the identification of seasonal effects, facility-specific factors, and other variables that may affect breeding success. This trend analysis is essential for optimizing breeding protocols and timing to achieve consistent results.

Comparative analysis functionality enables operators to evaluate the performance of different genetic lines, breeding strategies, or facility configurations. This comparative capability is essential for making informed decisions about breeding program direction and resource allocation.

Statistical analysis integration provides access to comprehensive statistical tools that support detailed evaluation of breeding program performance and identification of significant factors affecting breeding success. This statistical capability is essential for maintaining scientifically rigorous breeding programs and ensuring that breeding decisions are based on statistically valid analysis.

### Data Export and Integration

The reporting system includes comprehensive data export capabilities that enable operators to extract breeding and performance data for external analysis or integration with other systems. These export capabilities are essential for operations that maintain comprehensive databases or perform detailed statistical analysis using specialized software tools.

Excel export functionality provides immediate access to detailed breeding data in a format that supports further analysis using standard spreadsheet tools. This export capability is particularly valuable for operations that perform custom analysis or maintain comprehensive breeding databases outside the Fishtalk system.

Report formatting options enable operators to customize the presentation and organization of exported data to match their specific analysis requirements or reporting standards. This formatting flexibility ensures that exported data can be efficiently integrated into existing analysis workflows and reporting systems.

Data integration capabilities enable the breeding and performance data captured through the Broodstock module to be accessed by other components of the Fishtalk system, supporting comprehensive analysis that spans the entire production cycle from breeding through harvest.

The export system maintains complete data integrity and traceability, ensuring that exported data accurately represents the breeding operations and performance outcomes recorded within the system. This integrity is essential for maintaining confidence in analysis results and ensuring that breeding decisions are based on accurate and complete information.


## System Configuration

The System Configuration components of the Broodstock module provide comprehensive functionality for customizing the system to match specific operational requirements and regulatory standards. These configuration capabilities are essential for ensuring that the system operates effectively within the unique constraints and requirements of each breeding operation.

### Global List Management

Global list management provides the foundation for customizing the Broodstock module to match specific operational requirements and terminology. These lists define the available options for various data fields throughout the system and can be customized to reflect the specific protocols, regulations, and operational procedures used by each facility.

Mortality Causes configuration enables operators to define the specific mortality categories that are relevant to their operations and regulatory requirements. This customization ensures that mortality tracking provides meaningful information for analysis and reporting purposes while maintaining consistency with regulatory reporting requirements and operational protocols.

Culling Causes configuration provides similar functionality for planned removal categories, enabling operators to distinguish between different types of operational decisions and maintain detailed records of the reasons for population reductions. This distinction is essential for analyzing operational effectiveness and identifying opportunities for process improvement.

Treatment Causes and Medicaments configuration enables operators to maintain comprehensive lists of therapeutic interventions and medications that are available for use in their operations. These lists support detailed treatment tracking and regulatory compliance while ensuring that treatment protocols are properly documented and analyzed.

Environment Parameters configuration enables operators to define the specific environmental factors that are monitored and recorded in their operations. This customization ensures that environmental tracking captures the most relevant information for analysis and regulatory compliance purposes.

Method of Shocking configuration provides specialized functionality for operations that use shocking procedures, enabling operators to define the specific methods and protocols that are used in their facilities. This customization ensures that shocking procedures are properly documented and that performance analysis reflects the actual methods used.

### Parameter Customization for Individual Fish

Parameter customization for individual fish provides sophisticated functionality for defining the specific data fields that are captured and tracked for pit tagged individuals. This customization capability is essential for operations that have specific research requirements or regulatory obligations that require tracking of specialized data points.

Field format specification enables operators to define whether each parameter should be captured as Text, Date, Number, or Boolean (True/False) values. This format specification ensures that data validation and analysis functions operate correctly while providing flexibility for different types of information.

Parameter addition functionality enables operators to add new tracking parameters as their requirements evolve or as new research objectives are identified. This flexibility ensures that the system can adapt to changing requirements without requiring system modifications or data migration procedures.

The parameter customization system maintains complete integration with the pit tagging import functionality, ensuring that customized parameters can be included in file import operations and that mapping templates can accommodate facility-specific data requirements.

### Template Management Systems

Template management systems provide comprehensive functionality for saving and reusing configuration settings across multiple import operations. These systems are essential for operations that regularly process data from standardized sources or that need to maintain consistency across multiple data collection and import procedures.

Import template functionality enables operators to save field mapping configurations for both pit tag imports and spawning data imports. These templates eliminate the need to repeat mapping procedures for files with consistent formats and ensure that data is processed consistently across multiple import operations.

Template naming and organization capabilities enable operators to maintain multiple templates for different data sources or operational requirements. This organization capability is essential for operations that work with multiple data formats or that have different import requirements for different types of breeding operations.

Template sharing and backup functionality ensures that import configurations can be preserved and transferred between different system installations or operational locations. This capability is essential for maintaining operational continuity and ensuring that data processing procedures remain consistent across different facilities or time periods.

### Integration with Broader Fishtalk System

Integration with the broader Fishtalk system ensures that the Broodstock module operates seamlessly with other system components and that breeding data is properly incorporated into comprehensive production management and analysis systems. This integration is essential for maintaining data consistency and ensuring that breeding operations support broader production objectives.

Production stage integration ensures that breeding operations are properly connected to subsequent production phases and that genetic and performance information is preserved throughout the entire production cycle. This integration is essential for comprehensive performance analysis and genetic management.

Inventory management integration ensures that breeding operations are properly reflected in facility inventory tracking and that population counts and biomass calculations remain accurate throughout all breeding and production activities.

Reporting system integration ensures that breeding data is available for comprehensive analysis that spans the entire production cycle and that breeding performance can be correlated with subsequent production outcomes and market performance.

## Troubleshooting

The Troubleshooting section provides comprehensive guidance for resolving common issues that may arise during the operation of the Broodstock module, particularly those related to file import operations and system configuration. These troubleshooting procedures are essential for maintaining operational continuity and ensuring that data processing operations complete successfully.

### Excel File Import Issues

Excel file import issues represent the most common technical challenges encountered when using the Broodstock module, particularly when importing pit tag data or spawning information from external sources. These issues typically arise from configuration problems with Microsoft Office installations or missing system components that are required for Excel file processing.

The primary troubleshooting approach involves configuring Microsoft Office 2007 to ensure that the .NET Programmability Support component is properly installed and configured. This component is essential for enabling the Fishtalk system to read and process Excel files during import operations.

Configuration Method One represents the preferred approach for resolving Excel import issues and involves modifying the Microsoft Office 2007 installation through the Add or Remove Programs control panel. This method ensures that the necessary components are properly installed and configured within the existing Office installation.

The configuration process requires accessing the Microsoft Office 2007 entry in Add or Remove Programs and selecting the Change option to modify the installation. The Add or Remove Features option provides access to the detailed component configuration where the .NET Programmability Support can be verified and modified as needed.

Microsoft Office Excel expansion within the component configuration interface provides access to the .NET Programmability Support setting, which must be set to "Run from My Computer" to enable proper integration with the Fishtalk system. This setting ensures that the necessary programming interfaces are available for file processing operations.

### Alternative Configuration Methods

Configuration Method Two provides an alternative approach for situations where the primary configuration method does not resolve the Excel import issues. This method involves installing the Microsoft Primary Interop Assemblies, which provide the necessary programming interfaces for Excel integration.

The Primary Interop Assemblies download is available directly from Microsoft and provides the necessary components for enabling Excel integration with .NET applications such as Fishtalk. The download process involves accessing the Microsoft website and downloading the PrimaryInteropAssembly.exe archive file.

Installation of the Primary Interop Assemblies involves extracting the downloaded archive to a selected directory and running the o2007pia.msi installer file. The installation process is automated and does not require user input, but proper installation can be verified through the Add or Remove Programs control panel.

Verification of successful Primary Interop Assemblies installation involves checking for the presence of "Microsoft Office 2007 Primary Interop Assemblies" in the Add or Remove Programs listing. This verification ensures that the necessary components are properly installed and available for use by the Fishtalk system.

### Data Import Validation

Data import validation procedures provide guidance for identifying and resolving data-related issues that may prevent successful import operations. These procedures are essential for ensuring that import operations complete successfully and that imported data is properly integrated into the system.

File format validation ensures that Excel files are properly formatted and contain the necessary data fields for successful import operations. This validation includes checking for proper column headers, data types, and required fields that are essential for the import process.

Data consistency validation ensures that imported data is consistent with existing system data and that relationships between different data elements are properly maintained. This validation is particularly important for spawning data imports where individual fish identifications must match existing pit tag records.

Duplicate record handling provides guidance for resolving situations where imported data conflicts with existing system records. The system includes automatic duplicate detection capabilities, but operators may need to resolve conflicts manually depending on the specific nature of the duplicates.

Error message interpretation provides guidance for understanding and resolving specific error messages that may be encountered during import operations. These error messages typically provide specific information about the nature of the problem and the steps required for resolution.

### System Performance Optimization

System performance optimization procedures provide guidance for maintaining optimal system performance when working with large volumes of breeding data or complex organizational structures. These procedures are essential for ensuring that the system remains responsive and efficient as data volumes grow over time.

Database maintenance procedures ensure that the underlying database remains optimized for the types of queries and operations that are common in breeding operations. Regular maintenance helps prevent performance degradation and ensures that reporting and analysis operations complete in reasonable time frames.

Data archiving procedures provide guidance for managing historical data that is no longer actively used but must be preserved for regulatory or analysis purposes. Proper archiving helps maintain system performance while ensuring that historical data remains accessible when needed.

User interface optimization provides guidance for configuring the system interface to match specific operational workflows and user preferences. These optimizations can significantly improve operational efficiency and reduce the time required for routine data entry and analysis tasks.

Network and connectivity optimization ensures that the system operates efficiently in networked environments and that data synchronization and backup operations do not interfere with normal operational activities.

---

## Conclusion

The Fishtalk Control 4.4 Broodstock module represents a comprehensive solution for managing the complex requirements of modern aquaculture breeding operations. Through its sophisticated integration of individual fish tracking, spawning management, nursery operations, and comprehensive reporting capabilities, the module provides operators with the tools necessary to maintain genetic integrity, optimize breeding performance, and ensure regulatory compliance.

The module's design philosophy emphasizes complete traceability and data-driven decision making, enabling operators to build and maintain breeding programs that consistently produce high-quality offspring while supporting continuous improvement through detailed performance analysis. The comprehensive reporting and analytics capabilities ensure that breeding decisions are based on solid data and that the long-term effectiveness of breeding strategies can be properly evaluated and optimized.

The flexibility and customization capabilities built into the module ensure that it can adapt to the specific requirements of different operations while maintaining the standardization and consistency that are essential for effective breeding program management. This combination of flexibility and standardization makes the module suitable for a wide range of breeding operations, from research facilities to large-scale commercial operations.

The integration with the broader Fishtalk system ensures that breeding operations are properly connected to subsequent production phases and that the genetic and performance information captured during breeding operations continues to provide value throughout the entire production cycle. This integration is essential for maintaining the comprehensive traceability and performance tracking that are increasingly required in modern aquaculture operations.

---

## References

[1] AKVA group ASA. (2019). Fishtalk Control 4.4 User Guide - Broodstock Module. Document Version FT_4.4_v.1, Pages 177-205.

