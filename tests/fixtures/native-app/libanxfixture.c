#include <jni.h>
/*
 * Linux-host musl/x86_64 JNI fixture, NOT an Android NDK/Bionic shared object.
 * No Android-only libc symbols or dependency resolution are exercised.
 */
JNIEXPORT jint JNICALL Java_org_anx_nativefixture_NativeActivity_nativeSum(
    JNIEnv *env, jobject instance, jint x, jint y) {
    (void)env;
    (void)instance;
    return x + y;
}
