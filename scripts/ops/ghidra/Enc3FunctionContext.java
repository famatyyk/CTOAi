import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressOverflowException;
import ghidra.program.model.address.AddressSetView;
import ghidra.program.model.listing.Function;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryAccessException;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;

public class Enc3FunctionContext extends GhidraScript {

    private static final String[] TARGET_FUNCTIONS = new String[] {
        "005d5900",
        "005d63a0",
        "005dc9a0",
        "005dea30",
        "005ceb30",
        "005cd050",
        "005cf2b0"
    };

    @Override
    protected void run() throws Exception {
        String outputDirArg = getScriptArgs().length > 0 ? getScriptArgs()[0] : "C:/Users/zycie/CTOAi/artifacts/enc3";
        File outputDir = new File(outputDirArg);
        outputDir.mkdirs();

        File contextFile = new File(outputDir, "enc3-ghidra-function-context.md");
        File decompFile = new File(outputDir, "enc3-ghidra-function-context-decomp.txt");

        try (PrintWriter writer = new PrintWriter(new FileWriter(contextFile))) {
            writer.println("# ENC3 Function Context");
            writer.println();
            writer.println("## Raw ENC3 Byte Hits");
            writer.println();
            List<Address> enc3Hits = searchEnc3Bytes();
            if (enc3Hits.isEmpty()) {
                writer.println("No raw byte hit found for `ENC3`.");
            }
            else {
                for (Address hit : enc3Hits) {
                    writer.println("- `" + hit + "`");
                    Reference[] refs = getReferencesTo(hit);
                    if (refs.length == 0) {
                        writer.println("  - Xrefs: none");
                    }
                    for (Reference ref : refs) {
                        Function func = getFunctionContaining(ref.getFromAddress());
                        writer.println("  - Xref from `" + ref.getFromAddress() + "` -> `" + (func != null ? func.getName() + " @ " + func.getEntryPoint() : "NO_FUNCTION") + "`");
                    }
                }
            }
            writer.println();

            DecompInterface decomp = new DecompInterface();
            decomp.openProgram(currentProgram);

            try (PrintWriter decompWriter = new PrintWriter(new FileWriter(decompFile))) {
                for (String addressText : TARGET_FUNCTIONS) {
                    Address address = toAddr(addressText);
                    Function function = getFunctionAt(address);
                    if (function == null) {
                        function = getFunctionContaining(address);
                    }
                    writer.println("## Target Function `" + addressText + "`");
                    writer.println();
                    if (function == null) {
                        writer.println("Function not found.");
                        writer.println();
                        continue;
                    }

                    writer.println("- Name: `" + function.getName() + "`");
                    writer.println("- Entry: `" + function.getEntryPoint() + "`");
                    writer.println("- Callers:");
                    Set<Function> callers = new LinkedHashSet<>();
                    for (Reference ref : getReferencesTo(function.getEntryPoint())) {
                        Function caller = getFunctionContaining(ref.getFromAddress());
                        if (caller != null) {
                            callers.add(caller);
                        }
                    }
                    if (callers.isEmpty()) {
                        writer.println("  - none");
                    }
                    for (Function caller : callers) {
                        writer.println("  - `" + caller.getName() + " @ " + caller.getEntryPoint() + "`");
                    }

                    writer.println("- Direct callees:");
                    Set<Function> callees = new LinkedHashSet<>();
                    AddressSetView body = function.getBody();
                    for (Address addr = body.getMinAddress(); addr != null && body.contains(addr); addr = addr.next()) {
                        for (Reference ref : getReferencesFrom(addr)) {
                            Function callee = getFunctionAt(ref.getToAddress());
                            if (callee != null) {
                                callees.add(callee);
                            }
                        }
                    }
                    if (callees.isEmpty()) {
                        writer.println("  - none");
                    }
                    for (Function callee : callees) {
                        writer.println("  - `" + callee.getName() + " @ " + callee.getEntryPoint() + "`");
                    }
                    writer.println();

                    decompWriter.println("============================================================");
                    decompWriter.println("FUNCTION: " + function.getName() + " @ " + function.getEntryPoint());
                    decompWriter.println("============================================================");
                    DecompileResults results = decomp.decompileFunction(function, 60, monitor);
                    if (results != null && results.decompileCompleted()) {
                        decompWriter.println(results.getDecompiledFunction().getC());
                    }
                    else {
                        decompWriter.println("DECOMPILATION_FAILED");
                    }

                    for (Function caller : callers) {
                        decompWriter.println();
                        decompWriter.println("----- CALLER: " + caller.getName() + " @ " + caller.getEntryPoint() + " -----");
                        results = decomp.decompileFunction(caller, 60, monitor);
                        if (results != null && results.decompileCompleted()) {
                            decompWriter.println(results.getDecompiledFunction().getC());
                        }
                        else {
                            decompWriter.println("DECOMPILATION_FAILED");
                        }
                    }
                    decompWriter.println();
                }
            }
        }
    }

    private List<Address> searchEnc3Bytes() throws MemoryAccessException {
        List<Address> hits = new ArrayList<>();
        Memory memory = currentProgram.getMemory();
        byte[] needle = new byte[] { 0x45, 0x4e, 0x43, 0x33 };
        for (MemoryBlock block : memory.getBlocks()) {
            if (!block.isInitialized() || !block.isRead()) {
                continue;
            }
            Address start = block.getStart();
            Address end = block.getEnd();
            Address hit = memory.findBytes(start, end, needle, null, true, monitor);
            while (hit != null) {
                hits.add(hit);
                Address next;
                try {
                    next = hit.addNoWrap(1);
                }
                catch (AddressOverflowException e) {
                    break;
                }
                if (next == null || next.compareTo(end) > 0) {
                    break;
                }
                hit = memory.findBytes(next, end, needle, null, true, monitor);
            }
        }
        return hits;
    }
}