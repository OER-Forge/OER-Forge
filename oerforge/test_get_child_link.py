import os
import unittest

# --- Copied from make.py ---
def get_child_link_for_test(section_dir, child_dir, output_path):
    """
    Simulate get_child_link logic for unit testing.
    """
    # Direct child: same folder as section index
    if section_dir == child_dir:
        link = os.path.basename(output_path)
    else:
        link = os.path.relpath(output_path, section_dir)
    # Strip only a single leading '../' or './' from the link, not recursively
    if link.startswith('../'):
        link = link[3:]
    elif link.startswith('./'):
        link = link[2:]
    return link


class TestGetChildLink(unittest.TestCase):
    def test_section_index_direct_child(self):
        section_index = 'build/physics/index.html'
        child_output = 'build/physics/newton.html'
        link = get_child_link_for_test(os.path.dirname(section_index), os.path.dirname(child_output), child_output)
        self.assertEqual(link, 'newton.html')
        self.assertNotIn('..', link)

    def test_section_index_grandchild(self):
        section_index = 'build/physics/index.html'
        child_output = 'build/physics/mechanics/forces.html'
        link = get_child_link_for_test(os.path.dirname(section_index), os.path.dirname(child_output), child_output)
        self.assertEqual(link, 'mechanics/forces.html')
        self.assertNotIn('..', link)

    def test_section_index_deep_grandchild(self):
        section_index = 'build/physics/index.html'
        child_output = 'build/physics/mechanics/dynamics/energy.html'
        link = get_child_link_for_test(os.path.dirname(section_index), os.path.dirname(child_output), child_output)
        self.assertEqual(link, 'mechanics/dynamics/energy.html')
        self.assertNotIn('..', link)

    def test_section_index_sibling(self):
        section_index = 'build/physics/index.html'
        child_output = 'build/physics/einstein.html'
        link = get_child_link_for_test(os.path.dirname(section_index), os.path.dirname(child_output), child_output)
        self.assertEqual(link, 'einstein.html')
        self.assertNotIn('..', link)

    def test_section_index_nested_grandchild(self):
        section_index = 'build/physics/index.html'
        child_output = 'build/physics/quantum/wave.html'
        link = get_child_link_for_test(os.path.dirname(section_index), os.path.dirname(child_output), child_output)
        self.assertEqual(link, 'quantum/wave.html')
        self.assertNotIn('..', link)

    def test_section_index_to_self(self):
        section_index = 'build/physics/index.html'
        child_output = 'build/physics/index.html'
        link = get_child_link_for_test(os.path.dirname(section_index), os.path.dirname(child_output), child_output)
        self.assertEqual(link, 'index.html')
        self.assertNotIn('..', link)

    def test_no_escape_build(self):
        # Should never reference outside build/
        section_index = 'build/physics/index.html'
        child_output = 'build/physics/../newton.html'
        link = get_child_link_for_test(os.path.dirname(section_index), os.path.dirname(child_output), child_output)
        self.assertNotIn('..', link)

if __name__ == '__main__':
    unittest.main()
