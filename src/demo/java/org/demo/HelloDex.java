package org.demo;

/** Standalone DEX smoke entry point with no ANX framework dependencies. */
public final class HelloDex {
    private HelloDex() { }

    public static void main(String[] args) {
        System.out.println("[hello-dex] ART executed DEX bytecode.");
    }
}
