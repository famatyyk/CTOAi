import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import docking.options.OptionsService;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.framework.plugintool.PluginTool;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.CodeUnit;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Listing;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolIterator;
import ghidra.program.model.symbol.SymbolTable;

public class Enc3StringXrefs extends GhidraScript {

    private static final String[] TARGETS = new String[] {
        "ENC3",
        "unable to decrypt file",
        "decrypt",
        "encrypt",
        "otmod",
        "sandboxed",
        "onLoad"
    };

    @Override
    protected void run() throws Exception {
        String outputDirArg = getScriptArgs().length > 0 ? getScriptArgs()[0] : "C:/Users/zycie/CTOAi/artifacts/enc3";
        File outputDir = new File(outputDirArg);
        outputDir.mkdirs();

        File summaryFile = new File(outputDir, "enc3-ghidra-string-xrefs.md");
        File decompFile = new File(outputDir, "enc3-ghidra-candidate-decomp.txt");

        Listing listing = currentProgram.getListing();
        SymbolTable symbolTable = currentProgram.getSymbolTable();
        Map<String, List<Address>> hits = new LinkedHashMap<>();
        Map<String, List<Function>> functionsByTarget = new LinkedHashMap<>();

        for (String target : TARGETS) {
            hits.put(target, new ArrayList<>());
            functionsByTarget.put(target, new ArrayList<>());
        }

        monitor.setMessage("Scanning defined strings...");
        Data data = listing.getDefinedDataAt(currentProgram.getMinAddress());
        for (Data current = listing.getDefinedDataAt(currentProgram.getMinAddress()); current != null; current = listing.getDefinedDataAfter(current.getAddress())) {
            if (monitor.isCancelled()) {
                break;
            }
            Object value = current.getValue();
            if (!(value instanceof String)) {
                continue;
            }
            String stringValue = (String) value;
            for (String target : TARGETS) {
                if (stringValue.contains(target)) {
                    hits.get(target).add(current.getAddress());
                    Reference[] refs = getReferencesTo(current.getAddress());
                    for (Reference ref : refs) {
                        Function function = getFunctionContaining(ref.getFromAddress());
                        if (function != null && !functionsByTarget.get(target).contains(function)) {
                            functionsByTarget.get(target).add(function);
                        }
                    }
                }
            }
        }

        try (PrintWriter writer = new PrintWriter(new FileWriter(summaryFile))) {
            writer.println("# ENC3 Ghidra String Xrefs");
            writer.println();
            writer.println("Program: `" + currentProgram.getName() + "`");
            writer.println();
            for (String target : TARGETS) {
                writer.println("## Target: `" + target + "`");
                writer.println();
                List<Address> addresses = hits.get(target);
                if (addresses.isEmpty()) {
                    writer.println("No string hit found.");
                    writer.println();
                    continue;
                }
                for (Address address : addresses) {
                    writer.println("- String address: `" + address + "`");
                    CodeUnit cu = listing.getCodeUnitAt(address);
                    if (cu != null) {
                        writer.println("  - Representation: `" + cu.toString().replace("`", "'") + "`");
                    }
                    Reference[] refs = getReferencesTo(address);
                    if (refs.length == 0) {
                        writer.println("  - Xrefs: none");
                    }
                    for (Reference ref : refs) {
                        Function function = getFunctionContaining(ref.getFromAddress());
                        String functionName = function != null ? function.getName() + " @ " + function.getEntryPoint() : "NO_FUNCTION";
                        writer.println("  - Xref from: `" + ref.getFromAddress() + "` -> `" + functionName + "`");
                    }
                }
                writer.println();
            }
        }

        PluginTool tool = state != null ? state.getTool() : null;
        DecompileOptions options = new DecompileOptions();
        if (tool != null) {
            OptionsService service = tool.getService(OptionsService.class);
            if (service != null) {
                options.grabFromToolAndProgram(null, service.getOptions("Decompiler"), currentProgram);
            }
        }
        DecompInterface decomp = new DecompInterface();
        decomp.setOptions(options);
        decomp.openProgram(currentProgram);

        try (PrintWriter writer = new PrintWriter(new FileWriter(decompFile))) {
            writer.println("ENC3 candidate function decompilation");
            writer.println("Program: " + currentProgram.getName());
            writer.println();
            for (String target : TARGETS) {
                writer.println("============================================================");
                writer.println("TARGET: " + target);
                writer.println("============================================================");
                for (Function function : functionsByTarget.get(target)) {
                    writer.println();
                    writer.println("FUNCTION: " + function.getName() + " @ " + function.getEntryPoint());
                    DecompileResults results = decomp.decompileFunction(function, 60, monitor);
                    if (results != null && results.decompileCompleted()) {
                        writer.println(results.getDecompiledFunction().getC());
                    } else {
                        writer.println("DECOMPILATION_FAILED");
                    }
                }
                writer.println();
            }
        }

        println("Wrote: " + summaryFile.getAbsolutePath());
        println("Wrote: " + decompFile.getAbsolutePath());
    }
}