# NPC

## Technical Specification: NPC Interaction & Dialogue Branching

The dialogue engine for The Chronicler must evaluate a persistent state flag `last_run_result` (Enum: `INIT`, `VICTORY`, `DEFEAT`) upon scene initialization in `ZONE_SANCTUARY`:

1. **State: INIT (Fresh Game Boot)**
   - Dialogue Pool: `Standard_Greetings`
   - Tone: Friendly, informative, objective guidance.
   - Example line: *"Welcome back to the Scriptorium, Reader. The pages are waiting whenever you are ready to begin."*

2. **State: DEFEAT (Player just died to a Night Boss)**
   - Dialogue Pool: `Distant_Greetings`
   - Tone: Soft, hesitant, distracted, lower text-scrolling speed.
   - Example line: *"You return... cold. I can still smell the burning ink on your hands. Please... give me a moment of quiet before you open the cover again."*

3. **State: VICTORY (Player just cleared the Final Boss)**
   - Dialogue Pool: `Exalted_Greetings`
   - Tone: Warm, celebratory, highly positive, slightly accelerated text speed.
   - Example line: *"You did it! The wash was beautiful—the pages inside me felt completely clear for the first time in an age. You are a master editor, my friend!"*

## State Reset Rule
- As soon as the player interacts with The Chronicle book object to initialize a new run, the engine must force reset `last_run_result` back to `INIT` behind the scenes, ensuring the dialogue tracking is ready for the next return sequence.
