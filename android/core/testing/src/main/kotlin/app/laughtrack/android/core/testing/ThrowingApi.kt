package app.laughtrack.android.core.testing

import java.lang.reflect.Proxy

/**
 * Builds an implementation of [T] whose every method call fails the test, for
 * collaborators a scenario must never touch. Compose partial fakes from it with
 * interface delegation: class FakeShowsApi : ShowsApi by throwingApi().
 */
inline fun <reified T : Any> throwingApi(): T =
    Proxy.newProxyInstance(T::class.java.classLoader, arrayOf(T::class.java)) { _, method, _ ->
        error("Unexpected ${method.name} call")
    } as T
