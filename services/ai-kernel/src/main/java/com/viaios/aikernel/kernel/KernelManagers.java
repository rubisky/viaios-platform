package com.viaios.aikernel.kernel;

/**
 * AI Kernel — 11 Manager registry.
 * <p>
 * The AI Kernel is the core of VIAIOS, analogous to the Linux Kernel.
 * It manages all AI resources through 11 specialized managers.
 * Each manager is a first-class component with its own lifecycle,
 * API surface, and internal state machine.
 */
public final class KernelManagers {

    private KernelManagers() {}

    /** Registered manager names — used for API routing and health checks. */
    public static final String RESOURCE   = "ResourceManager";
    public static final String MODEL      = "ModelManager";
    public static final String AGENT      = "AgentManager";
    public static final String CAPABILITY = "CapabilityManager";
    public static final String WORKFLOW   = "WorkflowManager";
    public static final String PLUGIN     = "PluginManager";
    public static final String EVENT      = "EventManager";
    public static final String MEMORY     = "MemoryManager";
    public static final String POLICY     = "PolicyEngine";
    public static final String SECURITY   = "SecurityEngine";
    public static final String TELEMETRY  = "TelemetryEngine";

    public static final String[] ALL = {
        RESOURCE, MODEL, AGENT, CAPABILITY, WORKFLOW, PLUGIN,
        EVENT, MEMORY, POLICY, SECURITY, TELEMETRY
    };
}
