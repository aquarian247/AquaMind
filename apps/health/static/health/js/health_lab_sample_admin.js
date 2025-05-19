// Ensure this script is loaded after jQuery
(function($) {
    $(document).ready(function() {
        const sampleDateField = $('#id_sample_date');
        const assignmentField = $('#id_batch_container_assignment');
        // The URL for our AJAX view - this needs to be defined in your urls.py
        // We'll use a placeholder for now and update it once the URL is created.
        // It's common to pass this URL from the template using a data attribute or Django's 'reverse'.
        // For admin, we might hardcode it or make it discoverable via a script tag in the admin template override.
        // For simplicity here, let's assume a fixed path that we will create.
        const ajaxUrl = '/health/ajax/load-batch-assignments/'; 

        function loadAssignments() {
            const sampleDate = sampleDateField.val();
            if (!sampleDate) {
                assignmentField.html('<option value="">--- Select a sample date first ---</option>');
                return;
            }

            $.ajax({
                url: ajaxUrl,
                data: {
                    'sample_date': sampleDate
                },
                success: function(data) {
                    let options = '<option value="">---------</option>';
                    if (data && data.assignments) {
                        $.each(data.assignments, function(key, value) {
                            options += '<option value="' + value.id + '">' + value.text + '</option>';
                        });
                    }
                    assignmentField.html(options);
                },
                error: function() {
                    console.error('Error loading batch container assignments.');
                    assignmentField.html('<option value="">Error loading assignments</option>');
                }
            });
        }

        // Load assignments when sample_date changes
        sampleDateField.on('change', loadAssignments);

        // Initial load if sample_date already has a value (e.g., when editing an existing record or if a default is set)
        if (sampleDateField.val()) {
            loadAssignments();
        }
    });
})(jQuery);
