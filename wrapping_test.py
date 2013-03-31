
import inspect
import unittest

import binding
import errors
import wrapping


# TODO(kurts): have only one FakeInjector for tests.
class FakeInjector(object):

    def provide(self, cls):
        return self._provide_class(cls, _UNUSED_BINDING_CONTEXT)

    def _provide_class(self, cls, binding_context):
        return 'a-provided-{0}'.format(cls.__name__)

    def _provide_from_binding_key(self, binding_key, binding_context):
        return 'provided with {0}'.format(binding_key)

    def _call_with_injection(self, provider_fn, binding_context):
        return provider_fn()


# TODO(kurts): have only one call_provisor_fn() for tests.
_UNUSED_BINDING_CONTEXT = binding.BindingContext('unused', 'unused')
def call_provisor_fn(a_binding):
    return a_binding.proviser_fn(_UNUSED_BINDING_CONTEXT, FakeInjector())


class AnnotateTest(unittest.TestCase):

    def test_adds_binding_in_pinject_decorated_fn(self):
        @wrapping.annotate('foo', 'an-annotation')
        def some_function(foo):
            return foo
        self.assertEqual([binding.BindingKeyWithAnnotation('foo', 'an-annotation')],
                         [b.binding_key for b in getattr(some_function,
                                                         wrapping._ARG_BINDINGS_ATTR)])
        self.assertEqual(['provided with the arg name foo annotated with an-annotation'],
                         [call_provisor_fn(b)
                          for b in getattr(some_function, wrapping._ARG_BINDINGS_ATTR)])


class InjectTest(unittest.TestCase):

    def test_adds_binding_in_wrapped_fn(self):
        @wrapping.inject('foo', with_instance=3)
        def some_function(foo):
            return foo
        self.assertEqual([binding.BindingKeyWithoutAnnotation('foo')],
                         [b.binding_key for b in getattr(some_function,
                                                         wrapping._ARG_BINDINGS_ATTR)])
        self.assertEqual([3],
                         [call_provisor_fn(b)
                          for b in getattr(some_function, wrapping._ARG_BINDINGS_ATTR)])


class ProvidesTest(unittest.TestCase):

    def test_adds_provided_binding_key_in_wrapped_fn(self):
        @wrapping.provides('foo')
        def some_function():
            return 'a-foo'
        [provided_binding] = getattr(some_function, wrapping._PROVIDED_BINDINGS_ATTR)
        self.assertEqual(binding.BindingKeyWithoutAnnotation('foo'),
                         provided_binding.binding_key)
        self.assertEqual('a-foo', call_provisor_fn(provided_binding))

    def test_adds_annotation_and_scope_to_wrapped_fn(self):
        @wrapping.provides('foo', annotated_with='bar', in_scope='a-scope')
        def some_function():
            return 'a-foo'
        [provided_binding] = getattr(some_function, wrapping._PROVIDED_BINDINGS_ATTR)
        self.assertEqual(binding.BindingKeyWithAnnotation('foo', 'bar'),
                         provided_binding.binding_key)
        self.assertEqual('a-scope', provided_binding.scope_id)


class GetPinjectWrapperTest(unittest.TestCase):

    def test_sets_recognizable_wrapper_attribute(self):
        @wrapping.inject('foo', with_instance=3)
        def some_function(foo):
            return foo
        self.assertTrue(hasattr(some_function, wrapping._IS_WRAPPER_ATTR))

    def test_raises_error_if_referencing_nonexistent_arg(self):
        def do_bad_inject():
            @wrapping.inject('foo', with_instance=3)
            def some_function(bar):
                return bar
        self.assertRaises(errors.NoSuchArgToInjectError, do_bad_inject)

    def test_reuses_wrapper_fn_when_multiple_wrapping_decorators(self):
        @wrapping.inject('foo', with_instance=3)
        @wrapping.inject('bar', with_instance=4)
        def some_function(foo, bar):
            return foo + bar
        self.assertEqual([binding.BindingKeyWithoutAnnotation('bar'),
                          binding.BindingKeyWithoutAnnotation('foo')],
                         [b.binding_key
                          for b in getattr(some_function,
                                           wrapping._ARG_BINDINGS_ATTR)])

    def test_can_call_wrapped_fn_normally(self):
        @wrapping.inject('foo', with_instance=3)
        def some_function(foo):
            return foo
        self.assertEqual('an-arg', some_function('an-arg'))

    def test_can_introspect_wrapped_fn(self):
        @wrapping.inject('foo', with_instance=3)
        def some_function(foo, bar='BAR', *pargs, **kwargs):
            pass
        arg_names, varargs, keywords, defaults = inspect.getargspec(
            some_function)
        self.assertEqual(['foo', 'bar'], arg_names)
        self.assertEqual('pargs', varargs)
        self.assertEqual('kwargs', keywords)
        self.assertEqual(('BAR',), defaults)


class GetPrebindingsAndRemainingArgsTest(unittest.TestCase):
    # TODO(kurts)
    pass


class GetAnyProviderBindingKeysTest(unittest.TestCase):

    def test_gets_binding_keys_for_explicit_provider_fn(self):
        @wrapping.provides('arg_name')
        def some_function():
            return 'an-arg-name'
        [provider_binding] = wrapping.get_any_provider_bindings(some_function)
        self.assertEqual(binding.BindingKeyWithoutAnnotation('arg_name'),
                         provider_binding.binding_key)
        self.assertEqual('an-arg-name', call_provisor_fn(provider_binding))

    def test_gets_no_binding_keys_for_implicit_provider_fn(self):
        def new_arg_name():
            pass
        self.assertEqual(
            [], wrapping.get_any_provider_bindings(new_arg_name))

    def test_gets_no_binding_keys_for_arbitrary_fn(self):
        def some_function():
            pass
        self.assertEqual(
            [], wrapping.get_any_provider_bindings(some_function))