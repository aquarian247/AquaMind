# Understanding Fish Transfers in Fishtalk

This document provides a comprehensive summary of how fish transfers are managed within the Fishtalk system, drawing from both the main *Fishtalk User Guide* and the *Fishtalk Plan, Finance, & Optimizer User Guide*. It clarifies the different types of transfers, the concept of intermittent stages, and the integral role of the planning module in the overall workflow.

## Core Transfer Mechanisms in Fishtalk Control

The primary functionalities for moving **actual fish stock** are located in the Fishtalk Control module. These operations directly impact the live inventory and can be categorized into two main types: transfers occurring within a single site (intra-site) and transfers occurring between different sites (inter-site).

### Intra-Site Transfers (Within a Single Site)

When moving fish between units at the same physical site, Fishtalk provides two distinct methods. The choice between them depends on the complexity of the move and the level of detail required.

| Feature | Direct Transfer | Many-to-Many Transfer |
| :--- | :--- | :--- |
| **Primary Use** | For specific, traceable movements from designated source units to designated destination units. | For general redistribution or mixing of fish from multiple source units into multiple destination units. |
| **Unit Linking** | Requires explicit linking of each source unit to its destination unit(s). | Does not require explicit linking; the system treats the fish as a mixed group before redistributing them. |
| **Transfer Method** | Supports transfer by **Count & Average Weight** or by **Biomass & Average Weight**. | Only supports transfer by **Count & Average Weight**. |
| **Partial Transfers** | **Allowed.** You can transfer a portion of the fish, leaving the remaining stock in the source unit. | **Not Allowed.** All fish from the selected source units must be moved out. |
| **System Logic** | Creates distinct new fish groups in the destination units, maintaining a clear lineage. | Mixes the fish from all source units into a single logical group before distributing them to the destination units. This is reflected in the fish group history. |
| **Editing** | The last transfer for a specific unit can be edited or deleted. To edit an earlier transfer, subsequent ones must be deleted in reverse order. | Cannot be directly deleted. The action must be reversed by creating a new transfer to move the fish back to their original units. |

### Inter-Site Transfers (Between Different Sites)

Moving fish between separate sites, such as from a hatchery to a sea farm, involves a more complex, two-stage process designed to ensure accuracy and accountability. This process introduces the concept of a **Transport Container** as an intermittent holding stage.

> A **Transport Container** is a temporary logical entity within Fishtalk used to hold fish during the transit period between the source site and the destination site. It is not a physical unit but a placeholder in the system.

This two-step workflow is as follows:

1.  **Transfer Out:** At the **source site**, the user initiates a `Transfer Out`. Fish are moved from their source units into one or more of these logical Transport Containers. At this point, the fish have officially left the source site's inventory but have not yet arrived at the destination site's units. The system can generate a transport dispatch guide and track details of the journey.

2.  **Transfer In:** At the **destination site**, the pending arrival appears as a **Planned Activity** in the Activity grid. Once the fish physically arrive, the user initiates a `Transfer In`. This final step involves moving the fish from the logical Transport Containers into their specific destination units on the new site. The temporary Transport Containers are then automatically removed from the system.

This `Transfer Out / Transfer In` mechanism also comes in two variations, mirroring the logic of intra-site transfers:

*   **Normal Transfer:** Allows for one-to-one or one-to-many transfers between sites, with the ability to leave some fish behind in the source unit.
*   **Many-to-Many Transfer:** Used for moving the entire stock of multiple units from one site to another, where the fish are mixed during transit.

## The Role of the Planning & Finance Module

The complexity you are observing in the database, where plans for transfers exist, stems from the interaction between Fishtalk Control (actuals) and Fishtalk Plan (simulations).

The Fishtalk Plan module allows users to create detailed production plans and financial forecasts based on scenarios. These scenarios are built upon a snapshot of the actual production data from Fishtalk Control. Within a plan, users can simulate future actions, including transfers, to project outcomes without affecting live stock.

### Connecting Plans with Actual Transfers

The crucial link between a planned transfer and an executed one is primarily established through the **Sale of Live Fish** function in Fishtalk Control.

Here is the workflow that creates the planned transfers you are seeing:

1.  **Sale to Internal Receiver:** In Fishtalk Control, a user at a source site registers a `Sale of live fish`. Instead of selecting an external buyer, they choose the option **"Internal receiver in the same database"** and select the destination site.

2.  **Planned Activity Creation:** Upon saving this internal sale, the system does not immediately create a transfer. Instead, it automatically generates a **Planned Activity** at the **destination site**. This planned activity is an **Input** record, visible in the site's Activity grid.

3.  **Execution of the Input:** A user at the destination site then sees this pending input. They can open the record, which is pre-filled with all the details from the sale (fish group, count, weight, transport information), and execute the `Input of stock`. This final action is what formally receives the fish into the destination site's inventory, effectively completing the transfer that was initiated as a sale.

Therefore, the "plan for transfers" you are observing is this intermittent `Planned Activity` stage. A sale from one site creates a planned input at another, which then needs to be formally executed. This provides a layer of control and verification for the receiving site.

Additionally, the planning module has a feature that allows it to adjust its own simulated activities based on real-world events. When importing production data into a plan scenario, users can select an option to **"Move actions according to 1:1 transfers in actuals."** This means if a simple one-unit-to-one-unit transfer is executed in Fishtalk Control, the planning module can automatically shift any corresponding *planned* actions in its scenario to align with the new location of the fish, keeping the plan more consistent with reality.

---
*This summary was generated based on the Fishtalk v4.4 User Guides.*
