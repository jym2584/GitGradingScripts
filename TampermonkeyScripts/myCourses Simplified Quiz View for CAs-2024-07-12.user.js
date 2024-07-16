// ==UserScript==
// @name         myCourses Simplified Quiz View for CAs
// @namespace    http://tampermonkey.net/
// @version      2024-07-12
// @description  Simplifies the CA view of D2L quizzes for easier grading (mostly attendance based). Make sure to adjust the limit view and filters
// @author       jym2584
// @match        https://mycourses.rit.edu/d2l/lms/quizzing/admin/mark/quiz_mark_users.d2l?*
// @icon         https://www.google.com/s2/favicons?sz=64&domain=rit.edu
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

    function createStudentRow(name, score, publishDate) {
        let newRow = document.createElement('tr');

        // name
        let nameCell = document.createElement('td');
        nameCell.style.paddingRight = '10px';
        let nameStrong = document.createElement('strong');
        nameStrong.textContent = name;
        nameCell.appendChild(nameStrong);

        // score
        let scoreCell = document.createElement('td');
        scoreCell.style.paddingRight = '10px';
        scoreCell.style.textAlign = "right";

        // parse score
        let [num, denom] = score.split('/').map(str => parseFloat(str.trim()));
        let percentage = ((num / denom) * 100).toFixed(2);
        scoreCell.textContent = `${score} (${percentage}%)`;

        // publish stage
        let publishDateCell = document.createElement('td');
        publishDateCell.style.paddingLeft = '10px';
        publishDateCell.style.textAlign = "right";
        publishDateCell.textContent = publishDate;

        // Append cells to row
        newRow.appendChild(nameCell);
        newRow.appendChild(scoreCell);
        newRow.appendChild(publishDateCell);

        return newRow;
    }

    // Wait for the page to fully load before injecting table
    window.addEventListener('load', function() {
        let quizUI = document.getElementById('d_content_r_p');

        if (quizUI) {
            // Create parent div and table
            let mainDiv = document.createElement('div');
            mainDiv.style.padding = '30px';
            let studentsTable = document.createElement('table');
            mainDiv.appendChild(studentsTable);


            // Table headers
            let headerRow = document.createElement('tr');
            let headers = ['Name', 'Score', 'Publish Date'];
            headers.forEach(headerText => {
                let headerCell = document.createElement('th');
                headerCell.textContent = headerText;
                headerCell.style.padding = '8px';
                headerCell.style.fontSize = '20px';
                headerRow.appendChild(headerCell);
            });
            studentsTable.appendChild(headerRow);


            // Parse student rows from quiz page
            let studentRows = document.querySelectorAll('tr.d_gg');
            studentRows.forEach(studentRow => {
                let name = studentRow.querySelector('td > table > tbody > tr > td:nth-child(2)').innerText;
                let nextRow = studentRow.nextElementSibling;
                let score = nextRow.querySelector('td:nth-child(4) label').innerText;
                let publishDate = nextRow.querySelector('td:last-child label:last-child').innerText;

                // Create row element from student data
                let newRow = createStudentRow(name, score, publishDate);
                studentsTable.appendChild(newRow);
            });

            quizUI.parentNode.insertBefore(mainDiv, quizUI); // Append parent div before the quiz UI
        }
    }, false);
})();