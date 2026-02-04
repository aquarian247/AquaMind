# FishTalk Database ERD (Extract-Verified)

Last verified: 2026-02-04
Source: CSV extracts under `scripts/migration/data/extract/`
Scope: Only columns and relationships present in extracts. This is a partial view.

For broader schema notes and caveats, see `FISHTALK_SCHEMA_ANALYSIS.md`.

---

## 1. Core Entities (Input Projects -> Populations -> Containers)

```mermaid
erDiagram
    InputProjects {
        string InputProjectID PK
        string SiteID FK
        string Species
        string YearClass
        string ProjectNumber
        string ProjectName
        string Active
    }

    FishGroupHistory {
        string PopulationID FK
        string InputProjectID FK
    }

    Ext_Inputs_v2 {
        string PopulationID FK
        string InputName
        string InputNumber
        string YearClass
        string SupplierID
        datetime StartTime
        string InputCount
        string InputBiomass
        string Species
        string FishType
        string Broodstock
        string DeliveryID
        string Transporter
    }

    Populations {
        string PopulationID PK
        string ContainerID FK
        string Species
        datetime StartTime
        datetime EndTime
        string ProjectNumber
        string InputYear
        string RunningNumber
    }

    Ext_Populations_v2 {
        string PopulationID PK
        string ContainerID
        string PopulationName
        string SpeciesID
        datetime StartTime
        datetime EndTime
        string InputYear
        string InputNumber
        string RunningNumber
        string Fishgroup
    }

    Containers {
        string ContainerID PK
        string ContainerName
        string OrgUnitID FK
        string OfficialID
        string ContainerType
        string GroupID
    }

    OrganisationUnit {
        string OrgUnitID PK
        string Name
        string Latitude
        string Longitude
    }

    InputProjects ||--o{ FishGroupHistory : "project populations"
    FishGroupHistory }o--|| Populations : "population"
    Ext_Inputs_v2 }o--|| Populations : "population"
    Populations }o--|| Containers : "in container"
    Containers }o--|| OrganisationUnit : "at site"
    Ext_Populations_v2 }o--|| Populations : "same id"
```

Notes
- `Ext_Populations_v2` is a reporting view used for display names and fish group fields. Join on `PopulationID`.
- `Ext_Inputs_v2` is the main input batch feed (InputName/InputNumber/YearClass) and anchors a population.

---

## 2. Operations and Actions (Event Log Core)

```mermaid
erDiagram
    Operations {
        string OperationID PK
        datetime StartTime
        datetime EndTime
        string OperationType
        string Comment
        datetime RegistrationTime
    }

    Action {
        string ActionID PK
        string OperationID FK
        string PopulationID FK
        string ActionType
        string ActionOrder
    }

    PublicOperationTypes {
        string OperationType PK
        string TextID
        string Text
    }

    Operations ||--o{ Action : "contains"
    Action }o--|| Populations : "population"
    Operations }o--|| PublicOperationTypes : "type text"
```

Notes
- `ActionType` is the best available discriminator for domain tables (Feeding, Mortality, Treatment, etc).
- `OperationType` is a broader category (Transfer/Input/Harvest). See `public_operation_types.csv` and the mapping report in `analysis_reports/2026-02-04/`.

---

## 3. Transfers and Lineage

```mermaid
erDiagram
    SubTransfers {
        string SubTransferID PK
        string OperationID FK
        string SourcePopBefore FK
        string SourcePopAfter FK
        string DestPopBefore FK
        string DestPopAfter FK
        string TransferType
        string ShareCountFwd
        string ShareBiomFwd
        string ShareCountBwd
        string ShareBiomBwd
        string BranchedCount
        string BranchedBiomass
        datetime OperationTime
    }

    PopulationLink {
        string FromPopulationID FK
        string ToPopulationID FK
        string OperationID FK
        string LinkType
    }

    InternalDelivery {
        string SalesOperationID
        string InputSiteID
        string InputOperationID
        string PlannedActivityID
    }

    Ext_Transfers_v2 {
        string SourcePop
        string DestPop
        string TransferredCount
        string TransferredBiomassKg
        string ShareCountForward
        string ShareBiomassForward
        string ShareCountBackward
        string ShareBiomassBackward
    }

    SubTransfers }o--|| Operations : "operation"
    SubTransfers }o--o{ Populations : "lineage"
    PopulationLink }o--|| Operations : "operation"
    PopulationLink }o--o{ Populations : "link"
```

Notes
- `SubTransfers` is the canonical movement lineage table in extracts.
- `Ext_Transfers_v2` is a reporting extract without `OperationID` and should be treated as supplemental.
- `InternalDelivery` links sales and input operations but lacks unit-level details in current extracts.

---

## 4. Stage Events

```mermaid
erDiagram
    PopulationStages {
        string PopulationID FK
        string StageID FK
        datetime StartTime
    }

    OperationStageChanges {
        string OperationID FK
        string PopulationID FK
        string StageID FK
        datetime StageStartTime
        datetime OperationTime
    }

    ProductionStages {
        string StageID PK
        string StageName
    }

    PopulationStages }o--|| Populations : "population"
    PopulationStages }o--|| ProductionStages : "stage"
    OperationStageChanges }o--|| Operations : "operation"
    OperationStageChanges }o--|| Populations : "population"
    OperationStageChanges }o--|| ProductionStages : "stage"
```

---

## 5. Event Extracts (Feeding and Mortality)

These are derived extracts that already join Actions and Operations. They are not raw FishTalk tables.

```mermaid
erDiagram
    FeedingActions {
        string ActionID
        string PopulationID
        datetime FeedingTime
        string FeedAmountG
        string FeedBatchID
        string FeedTypeID
        string FeedTypeName
        string OperationComment
    }

    MortalityActions {
        string ActionID
        string PopulationID
        datetime OperationStartTime
        string MortalityCount
        string MortalityBiomass
        string MortalityCauseID
        string CauseText
        string Comment
    }

    FeedTypes {
        string FeedTypeID PK
        string Name
        string FeedSupplierID
    }

    FeedSuppliers {
        string FeedSupplierID PK
        string Name
    }

    FeedStores {
        string FeedStoreID PK
        string FeedStoreName
        string OrgUnitID
        string Active
        string Capacity
        string FeedStoreTypeID
    }

    FeedDeliveries {
        string FeedReceptionID PK
        string AmountKg
        string Price
        string FeedTypeID
        string FeedStoreID
        string SupplierID
        string BatchNumber
        datetime ReceptionDate
    }

    FeedingActions }o--|| FeedTypes : "feed type"
    FeedTypes }o--|| FeedSuppliers : "supplier"
    FeedDeliveries }o--|| FeedTypes : "feed type"
    FeedDeliveries }o--|| FeedStores : "store"
```

---

## 6. Status Snapshots

```mermaid
erDiagram
    StatusValues {
        string PopulationID FK
        datetime StatusTime
        string CurrentCount
        string CurrentBiomassKg
        string Temperature
    }

    StatusValues }o--|| Populations : "population"
```

---

## 7. Organization Views (Reporting)

```mermaid
erDiagram
    GroupedOrganisation {
        string ContainerID
        string Site
        string SiteGroup
        string Company
        string ProdStage
        string ContainerGroup
        string ContainerGroupID
        string StandName
        string StandID
    }

    GroupedOrganisation }o--|| Containers : "container"
```

---

## 8. Transport References

```mermaid
erDiagram
    TransportCarriers {
        string TransportCarrierID PK
        string Name
        string OfficialCode
        string TransportMethodID
        string ContactID
        string Active
    }

    TransportMethods {
        string TransportMethodID PK
        string TextID
        string DefaultText
        string Active
        string SystemDelivered
    }

    Ext_Transporters_v2 {
        string TransporterID PK
        string Name
    }

    TransportCarriers }o--|| TransportMethods : "method"
```

Notes
- These tables are reference data for carrier/method names. They are not yet linked to population movement in extracts.

