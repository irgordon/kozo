<p align="center">
  <a href="https://kozo.page"><img src="kozo-logo.svg" width="240" alt="KOZO: Made Simple, Designed Secure."></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Built_with-Zig-F7A41D?style=for-the-badge&logo=zig&logoColor=white" />
  <img src="https://img.shields.io/badge/Built_with-Rust-000000?style=for-the-badge&logo=rust&logoColor=#B7410E" />
  <img src="https://img.shields.io/badge/Platform-KOZO_Native-000000?style=for-the-badge&logo=linux&logoColor=white" />
  <img src="https://img.shields.io/badge/License-FOSS-000000?style=for-the-badge&logo=opensourceinitiative&logoColor=white" />
  <img src="https://img.shields.io/badge/Architectures-x86__64%20%7C%20ARM64-000000?style=for-the-badge" />
</p>

# **KOZO**

**KOZO** is a next-generation operating system built from the ground up for privacy, performance, and peace of mind. By combining the precision of **Zig** with the safety of **Rust**, KOZO creates a computing environment that is "Secure by Default" without sacrificing the apps you love.



## **Why KOZO?**

- **Built-In Privacy**
  In KOZO, your data isn't just "protected"—it's unreachable. Using a **Zero Trust** model, apps only see exactly what you allow them to see. No more hidden tracking, no more "ambient" access to your files.

- **Unmatched Stability**
  By isolating every part of the system (drivers, internet, files) into its own "sandbox," KOZO ensures that a crash in one app never takes down the whole computer. It’s an OS that stays out of your way and just works.

- **Run Your Favorite Apps**
  You don't have to switch your workflow. KOZO features a built-in compatibility layer that allows standard Linux applications to run safely and smoothly, but with enhanced security and privacy controls.

- **Performance Without Compromise**
  We use a "Microkernel" design—keeping the core of the OS tiny and lightning-fast. This means faster boot times, smoother multitasking, and better battery life on laptops.

- **Clear-Name Security**
  We've replaced confusing "permissions" with **Clear-Name** prompts. Instead of cryptic codes, KOZO asks you simple questions: *"Allow the Browser to access your Downloads folder?"* You are always in control.



## **Core Principles**

- **Simple & Modular**
  Every piece of KOZO does one thing and does it well. This makes the system easier to update, harder to break, and simpler to trust.

- **Defense-in-Depth**
  We assume threats exist and build layers of protection around your digital life. If one layer is ever compromised, the others remain locked tight.

- **Modern Foundations**
  Leveraging the latest in systems programming (Zig & Rust), KOZO avoids the "legacy baggage" of 40-year-old operating systems, focusing instead on the needs of today's users.

## **Project Structure**

* `kernel/`: The "Heart" of the system (Zig). High-precision, minimal code.
* `services/`: The "Brain" of the system (Rust). Safe, smart system logic.
* `scripts/`: The "Builder." Ensures every version of KOZO is perfectly crafted.

## **Status**

KOZO is currently in early, active development. We are laying the foundations for a stable, public release. Early adopters and developers are encouraged to follow our architectural specs for deep-dive technical details.

## **License**

MIT + Apache 2.0 (dual-licensed)

---
