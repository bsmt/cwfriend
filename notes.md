# cwfriend

A python library to augment ChipWhisperer.

Things it should do:
* Perform tedious, error-prone setup for you
    * Have configurations for common setups that you can just call and override minimally as necessary
    * For instance, a one-shot voltage glitching with external trigger setup would be handy
* Provide more advanced search strategies than just linearly iterating through your ranges
    * Can use the methods I learned about in that Riscure paper.
    * This will need the user to provide information about the result of each test case, which isn't too awful.
    * We might be able to hook into comms and identify a mute/reset condition at least.
* Handle aggregating test results and displaying them to the user in a useful fashion.
    * Plotting test results throughout the search space so one can easily identify interesting regions and investigate further
* Maybe even provide pre-made profiles for common targets
    * Say, STM32 readout protection :O
* Not get in the user's way.
    * IMO ChipWhisperer's library assumes you're using one of the tutorial examples in every aspect of its usage. If you're doing a real-world test on something, you have to try to dodge that stuff everywhere and it's annoying.

## Structure

### Configuration

Configure the chipwhisperer for a given testing situation. For instance, voltage glitching with external trigger. This is where the various scope.glitch, scope.clock, and scope.adc parameters are set. These can be somewhat generic.

### Context

Something to handle setting up and understanding your target's context. For instance with STM32 this should reset and start the bootloader for each iteration (send 7f to establish baud rate). Then it could maybe send the read command and setup the scope somehow. Perhaps it could handle interpreting results as well.

### Searching

Classes to choose parameters for you and run tests. The user could either manually handle the communications and result interpretation, which is currently what you'd do with Chipwhisperer, or some separate class could handle that.

It'd be nice if these could work in more concrete units than chipwhisperer's weird offset/width settings like ext_offset, offset, and fine_offset. I'd like to just give it a range of times. For instance, glitch from 10-60us from trigger with single pulses from 20-100ns.
